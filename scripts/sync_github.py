#!/usr/bin/env python3
"""Sync GitHub repositories into _data/generated/github.yml.

Collects the EthioNLP organisation's repositories, plus Ethiopian-language
repositories belonging to members who declared a `github:` handle, plus any
extra repositories pinned by hand in _data/ecosystem_manual.yml.

Set GITHUB_TOKEN to raise the rate limit from 60 to 5,000 requests an hour. The
GitHub Action passes the automatic token; locally the unauthenticated limit is
enough for one run.

Usage:  python3 scripts/sync_github.py [--dry-run]
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.common import (  # noqa: E402
    DATA,
    get_json,
    info,
    load_curated,
    looks_ethiopian,
    read_members,
    step,
    touch_meta,
    warn,
    write_generated,
)

API = "https://api.github.com"
ORG = "EthioNLP"

# Repository topic / name hints → focus area.
FOCUS_HINTS = [
    ("data", ("dataset", "corpus", "corpora", "annotation", "data")),
    ("models", ("llm", "model", "bert", "llama", "tokenizer", "embedding", "pretrain")),
    ("evaluation", ("benchmark", "eval", "shared-task", "semeval", "leaderboard")),
    ("applications", ("translation", "mt", "asr", "speech", "chatbot", "search", "app", "demo")),
    ("capacity", ("tutorial", "course", "workshop", "training", "template")),
    ("linguistics", ("morpholog", "pos", "syntax", "linguistic", "dialect")),
]


def auth_headers() -> dict:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def classify(repo: dict) -> str:
    blob = " ".join(
        [repo.get("name") or "", repo.get("description") or "", " ".join(repo.get("topics") or [])]
    ).lower()
    for focus, hints in FOCUS_HINTS:
        if any(h in blob for h in hints):
            return focus
    return "applications"


def normalise(repo: dict, owned: bool) -> dict:
    return {
        "id": repo.get("full_name"),
        "owner": (repo.get("owner") or {}).get("login"),
        "name": repo.get("name"),
        "url": repo.get("html_url"),
        "homepage": repo.get("homepage") or None,
        "description": (repo.get("description") or "").strip() or None,
        "language": repo.get("language"),
        "topics": (repo.get("topics") or [])[:6],
        "focus": classify(repo),
        "stars": repo.get("stargazers_count") or 0,
        "forks": repo.get("forks_count") or 0,
        "updated": (repo.get("pushed_at") or "")[:10] or None,
        "created": (repo.get("created_at") or "")[:10] or None,
        "license": ((repo.get("license") or {}) or {}).get("spdx_id"),
        "archived": bool(repo.get("archived")),
        "owned": owned,
    }


def fetch_repos(path: str) -> list[dict]:
    out, page = [], 1
    while page <= 4:  # 400 repos is far past anything we expect
        batch = get_json(f"{API}/{path}?per_page=100&sort=pushed&page={page}", auth_headers())
        if not batch:
            break
        out.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return out


def registered_teams() -> list[dict]:
    """Teams from _data/organisations.yml that declare a GitHub organisation."""
    path = DATA / "organisations.yml"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        entries = yaml.safe_load(fh) or []
    return [
        e for e in entries
        if (e.get("github") or "").strip()
        and (e.get("github") or "").strip().lower() != ORG.lower()
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    seen: dict[str, dict] = {}

    step(f"Organisation: {ORG}")
    org_repos = fetch_repos(f"orgs/{ORG}/repos")
    if not org_repos:
        warn(f"no repositories returned for {ORG} (rate limited? set GITHUB_TOKEN)")
    for repo in org_repos:
        if repo.get("fork"):
            continue
        item = normalise(repo, owned=True)
        seen[item["id"]] = item
    info(f"{len(seen)} repositories")

    # Registered teams are swept whether or not any of their people are listed
    # here, which is what lets a new team join and have its code appear.
    teams = registered_teams()
    if teams:
        step(f"Registered teams ({len(teams)})")
    for team in teams:
        org = team["github"].strip().rstrip("/").split("/")[-1]
        found = 0
        for repo in fetch_repos(f"orgs/{org}/repos"):
            if repo.get("fork") or repo.get("archived"):
                continue
            if not looks_ethiopian(
                repo.get("name") or "",
                repo.get("description") or "",
                " ".join(repo.get("topics") or []),
            ):
                continue
            item = normalise(repo, owned=True)
            item["team"] = team.get("slug")
            if team.get("lead"):
                item["member"] = team["lead"]
            if item["id"] not in seen:
                seen[item["id"]] = item
                found += 1
        info(f"{org} → {found}")

    members = read_members()
    handles = {
        (m.get("github") or "").strip().rstrip("/").split("/")[-1]: m["slug"]
        for m in members
        if m.get("github")
    }
    handles.pop("", None)

    step(f"Member accounts ({len(handles)})")
    for handle, slug in sorted(handles.items()):
        found = 0
        for repo in fetch_repos(f"users/{handle}/repos"):
            if repo.get("fork") or repo.get("archived"):
                continue
            if not looks_ethiopian(
                repo.get("name") or "",
                repo.get("description") or "",
                " ".join(repo.get("topics") or []),
            ):
                continue
            item = normalise(repo, owned=True)
            item["member"] = slug
            seen.setdefault(item["id"], item)
            found += 1
        info(f"{handle} → {found}")

    step("Pinned repositories from _data/ecosystem_manual.yml")
    curated = load_curated("ecosystem_manual.yml") or {}
    pinned = (curated or {}).get("github", []) if isinstance(curated, dict) else []
    for full_name in pinned:
        if full_name in seen:
            continue
        repo = get_json(f"{API}/repos/{full_name}", auth_headers())
        if repo:
            item = normalise(repo, owned=False)
            item["pinned"] = True
            seen[item["id"]] = item
    info(f"{len(pinned)} pinned")

    repos = sorted(seen.values(), key=lambda r: (-(r["stars"] or 0), r["id"] or ""))

    payload = {
        "totals": {
            "repos": len(repos),
            "stars": sum(r["stars"] for r in repos),
            "forks": sum(r["forks"] for r in repos),
        },
        "repos": repos,
    }

    if args.dry_run:
        print(f"\n{payload['totals']}")
        return 0

    write_generated("github.yml", payload, "sync_github.py", "ecosystem_manual.yml")
    touch_meta("github")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
