#!/usr/bin/env python3
"""Sync Hugging Face models and datasets into _data/generated/huggingface.yml.

Artifacts are sorted into three tiers, and the distinction is the whole point of
this script:

* ``ethionlp``, the EthioNLP organisation and the teams that have registered
  themselves in ``_data/organisations.yml``. This community built it.
* ``member``, the personal account of a confirmed member. Their own work.
* ``related``, Ethiopian-language work by anyone else, including
  organisations a member happens to belong to.

That last tier exists because of a mistake worth not repeating. Sweeping every
organisation a member belongs to and calling the results "ours" credited this
community with `bigscience/mt0` and a multilingual toxicity classifier, on the
strength of one member holding org membership. Belonging to an organisation is
not authorship. Only an explicit registration in ``_data/organisations.yml``, a human decision, reviewed in a pull request, promotes an organisation's work
to ``ethionlp``.

Four sources, in order of authority:

1. the ``EthioNLP`` organisation;
2. any ``huggingface:`` handle declared in a ``_members/*.md`` file, a member's
   own Ethiopian-language work counts as community work;
3. every Hub organisation the *verified* members belong to, discovered from
   their public profiles. Much of this community's most-used work is published
   under a lab or project org rather than under the EthioNLP org or a personal
   account, ``uhhlt/am-roberta`` is the clearest case, with more downloads than
   the EthioNLP organisation has in total. Only artifacts that pass the
   Ethiopian-language filter are kept, so belonging to a large general org does
   not drag that org's whole output onto the site;
4. a keyword sweep of the Hub for Ethiopian languages, which surfaces relevant
   work by people who have not joined yet. Those are kept in a separate
   ``related`` list and never mixed with the community's own output.

Usage:  python3 scripts/sync_huggingface.py [--dry-run]
"""

from __future__ import annotations

import argparse
import sys
import time
import urllib.parse
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.common import (  # noqa: E402
    DATA,
    ETHIOPIAN_LANGUAGES,
    get_json,
    info,
    language_names,
    looks_ethiopian,
    read_members,
    step,
    touch_meta,
    warn,
    write_generated,
)

API = "https://huggingface.co/api"
ORG = "EthioNLP"

SWEEP_TERMS = [
    "amharic", "tigrinya", "afaan oromo", "ethiopic", "geez", "wolaytta",
    "sidama", "ethiopian",
]

# pipeline_tag → the focus area the artifact belongs to on the site.
TASK_FOCUS = {
    "fill-mask": "models",
    "text-generation": "models",
    "text2text-generation": "models",
    "feature-extraction": "models",
    "sentence-similarity": "models",
    "translation": "applications",
    "text-classification": "applications",
    "token-classification": "applications",
    "question-answering": "applications",
    "automatic-speech-recognition": "applications",
    "summarization": "applications",
}


def normalise(record: dict, kind: str, owned: bool) -> dict:
    """Flatten one Hub record into the shape the templates consume."""
    tags = record.get("tags") or []
    card = record.get("cardData") or {}

    codes = []
    for tag in tags:
        if tag.startswith("language:"):
            codes.append(tag.split(":", 1)[1])
        elif tag in ETHIOPIAN_LANGUAGES:
            codes.append(tag)
    card_langs = card.get("language")
    if isinstance(card_langs, str):
        codes.append(card_langs)
    elif isinstance(card_langs, list):
        codes.extend(card_langs)

    # How much of this artifact is actually about Ethiopian languages.
    #
    # The organisation sweep reaches genuinely multilingual work, mt0 covers a
    # hundred-odd languages, of which Amharic is one; a multilingual toxicity
    # classifier likewise. A member did contribute to those, but presenting them
    # beside am-roberta as "Ethiopian language technology" would overclaim, and
    # their download counts would swamp the community's own figures. They are
    # kept and labelled rather than dropped.
    #
    # The breadth test counts language codes in the bare tags rather than in
    # cardData: the list endpoints return a truncated cardData, so mt0 arrives
    # here claiming two languages instead of 101, and only the per-model detail
    # endpoint has the full list. The bare tags do carry every code, at the cost
    # of this being a heuristic, hence the stoplist of short tags that are not
    # languages.
    NOT_LANGUAGES = {
        "ner", "pos", "llm", "ml", "nlp", "asr", "tts", "ocr", "mt", "qa",
        "gpt", "api", "rl", "cv", "ai", "sft", "dpo", "lm", "seq",
    }
    tag_codes = {
        tag for tag in tags
        if ":" not in tag and 2 <= len(tag) <= 3 and tag.isalpha()
        and tag.islower() and tag not in NOT_LANGUAGES
    }
    all_codes = tag_codes | {
        c.strip().lower() for c in codes if c and isinstance(c, str)
    }
    ethio_codes = {c for c in all_codes if c in ETHIOPIAN_LANGUAGES}

    breadth = "focused"
    if len(all_codes) > 4 and len(ethio_codes) * 2 < len(all_codes):
        breadth = "multilingual"

    full_id = record.get("id", "")
    owner, _, name = full_id.partition("/")

    task = record.get("pipeline_tag")
    focus = TASK_FOCUS.get(task or "", "models" if kind == "model" else "data")

    # Free-text tags only, the Hub mixes real topic tags with machine ones
    # (region:, license:, base_model:, format:) that are noise on a landing page.
    topics = [
        t for t in tags
        if ":" not in t
        and t not in ETHIOPIAN_LANGUAGES
        and t not in {"transformers", "pytorch", "jax", "safetensors", "datasets"}
    ][:6]

    return {
        "id": full_id,
        "owner": owner,
        "name": name or full_id,
        "kind": kind,
        "url": f"https://huggingface.co/{'datasets/' if kind == 'dataset' else ''}{full_id}",
        "task": task,
        "focus": focus,
        "languages": language_names(codes),
        "topics": topics,
        "license": card.get("license") or next(
            (t.split(":", 1)[1] for t in tags if t.startswith("license:")), None
        ),
        "size": next((t.split(":", 1)[1] for t in tags if t.startswith("size_categories:")), None),
        "downloads": record.get("downloads") or 0,
        "likes": record.get("likes") or 0,
        "created": (record.get("createdAt") or "")[:10] or None,
        "modified": (record.get("lastModified") or "")[:10] or None,
        "arxiv": next((t.split(":", 1)[1] for t in tags if t.startswith("arxiv:")), None),
        "owned": owned,
        # "focused", built for Ethiopian languages
        # "multilingual", broad work a member contributed to, Ethiopian
        #                  languages being a minority of its coverage
        "breadth": breadth,
        "language_count": len(all_codes),
    }


def fetch_author(author: str, kind: str) -> list[dict]:
    endpoint = "datasets" if kind == "dataset" else "models"
    time.sleep(THROTTLE)
    data = get_json(f"{API}/{endpoint}?author={urllib.parse.quote(author)}&full=true&limit=500")
    if data is None:
        warn(f"no {kind}s returned for {author}")
        return []
    return data if isinstance(data, list) else []


# The Hub rate-limits an unauthenticated client that fires a hundred requests
# back to back, and the retry backoff then costs far more than the requests
# saved. A short, deliberate pause between calls keeps the whole sweep under the
# limit and turns a twenty-minute run into a two-minute one.
THROTTLE = 0.35

# Identifiers that mark a member as verified, someone whose research output we
# are willing to attribute to this community sight unseen.
#
# This gate exists because of the organisation sweep below. Following the orgs
# of *every* listed member turned up 1,758 of them: the accounts imported from
# the Hugging Face organisation include people who have joined hundreds of
# unrelated orgs, and sweeping those would be thousands of requests returning
# almost nothing. The curated roster, the fourteen people carried over from the
# previous site, each with a Scholar, ORCID, OpenAlex or DBLP identifier, is
# the right population for this, and is what "models built by the verified
# members" means.
SCHOLARLY_IDS = ("openalex", "orcid", "scholar", "dblp", "semantic_scholar")


def is_verified(member: dict) -> bool:
    return bool(member.get("founder")) or any(member.get(k) for k in SCHOLARLY_IDS)


def all_teams() -> list[dict]:
    """Every entry in _data/organisations.yml, in file order."""
    path = DATA / "organisations.yml"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or []


def registered_teams() -> dict[str, dict]:
    """Teams declared in _data/organisations.yml, keyed by Hub org name.

    Registering a team is the route for a group whose people are not in
    `_members/` yet; a new lab can join and have its work appear without anyone
    being listed individually first.
    """
    teams = {}
    for entry in all_teams():
        org = (entry.get("huggingface") or "").strip()
        if org and org.lower() != ORG.lower():
            teams[org] = entry
    return teams


def fetch_orgs(handle: str) -> list[str]:
    """The Hub organisations a user belongs to, from their public profile."""
    time.sleep(THROTTLE)
    data = get_json(f"{API}/users/{urllib.parse.quote(handle)}/overview")
    if not isinstance(data, dict):
        return []
    return [
        (org.get("name") or "").strip()
        for org in (data.get("orgs") or [])
        if (org.get("name") or "").strip()
    ]


def fetch_search(term: str, kind: str) -> list[dict]:
    endpoint = "datasets" if kind == "dataset" else "models"
    data = get_json(
        f"{API}/{endpoint}?search={urllib.parse.quote(term)}&full=true&limit=60&sort=downloads"
    )
    return data if isinstance(data, list) else []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="print, do not write")
    args = parser.parse_args()

    members = read_members()
    # Someone who has not confirmed their listing is not presented as a member,
    # but their Ethiopian-language work is still worth showing, as work, in the
    # related tier, not as this community's output.
    confirmed = {m["slug"] for m in members if m.get("confirmed") is not False}
    member_handles = {}
    for m in members:
        handle = (m.get("huggingface") or "").strip().rstrip("/").split("/")[-1]
        if handle and handle.lower() != ORG.lower():
            member_handles[handle] = m["slug"]

    seen: dict[str, dict] = {}

    # Read once: used to tag the EthioNLP org below and swept in full further
    # down, so a team can join without any of its people being listed here.
    teams = registered_teams()
    own_team = next(
        (e.get("slug") for e in (all_teams() or [])
         if (e.get("huggingface") or "").lower() == ORG.lower()),
        None,
    )

    step(f"Organisation: {ORG}")
    for kind in ("model", "dataset"):
        for rec in fetch_author(ORG, kind):
            item = normalise(rec, kind, owned=True)
            if own_team:
                item["team"] = own_team
            seen[item["id"]] = item
    info(f"{sum(1 for i in seen.values() if i['kind'] == 'model')} models, "
         f"{sum(1 for i in seen.values() if i['kind'] == 'dataset')} datasets")

    step(f"Member accounts ({len(member_handles)})")
    for handle, slug in sorted(member_handles.items()):
        found = 0
        for kind in ("model", "dataset"):
            for rec in fetch_author(handle, kind):
                item = normalise(rec, kind, owned=True)
                if not item["languages"] and not looks_ethiopian(item["id"], " ".join(item["topics"])):
                    continue  # a member's unrelated side project is not community work
                item["tier"] = "member" if slug in confirmed else "related"
                if slug in confirmed:
                    item["member"] = slug
                else:
                    item["via_member"] = slug
                seen.setdefault(item["id"], item)
                found += 1
        info(f"{handle} → {found}")
    if not member_handles:
        info("none declared yet, add `huggingface:` to a file in _members/")

    # ── Tier the artifacts collected so far ──────────────────────────────────
    for item in seen.values():
        item.setdefault("tier", "ethionlp")

    step("Organisations the verified members belong to")
    # Discovered rather than hard-coded: a verified member joining a new lab org
    # is picked up on the next sync without anyone editing this file.
    verified = {m["slug"] for m in members if is_verified(m)}
    verified_handles = {h: s for h, s in member_handles.items() if s in verified}
    info(f"{len(verified_handles)} of {len(member_handles)} member accounts are verified")

    orgs: dict[str, set[str]] = {}
    for handle, slug in sorted(verified_handles.items()):
        for org in fetch_orgs(handle):
            if org.lower() == ORG.lower():
                continue
            orgs.setdefault(org, set()).add(slug)

    # Teams that registered themselves are swept whether or not any of their
    # people are listed here yet. This is what makes a new team joining work.
    for org, entry in teams.items():
        bucket = orgs.setdefault(org, set())
        if entry.get("lead"):
            bucket.add(entry["lead"])
    if teams:
        info(f"{len(teams)} registered teams: {', '.join(sorted(teams))}")

    if orgs:
        info(f"{len(orgs)} organisations: {', '.join(sorted(orgs))}")
    for org, slugs in sorted(orgs.items()):
        found = 0
        for kind in ("model", "dataset"):
            for rec in fetch_author(org, kind):
                item = normalise(rec, kind, owned=True)
                # The same filter as for personal accounts. Members belong to
                # plenty of orgs, bigscience, masakhane, a conference org, # whose non-Ethiopian output is not this community's work.
                if not item["languages"] and not looks_ethiopian(item["id"], " ".join(item["topics"])):
                    continue
                item["org"] = org
                team = teams.get(org)
                if team:
                    # Registered: a human vouched for this organisation.
                    item["team"] = team.get("slug")
                    item["tier"] = "ethionlp"
                    if slugs:
                        item["member"] = sorted(slugs)[0]
                else:
                    # Merely discovered. A member belongs to this org, which is
                    # worth surfacing, but it is not evidence they wrote this.
                    item["tier"] = "related"
                    item["via_member"] = sorted(slugs)[0] if slugs else None
                if item["id"] not in seen:
                    seen[item["id"]] = item
                    found += 1
        if found:
            info(f"{org} → {found}")

    step("Ethiopian-language sweep of the Hub")
    related: dict[str, dict] = {}
    for term in SWEEP_TERMS:
        for kind in ("model", "dataset"):
            for rec in fetch_search(term, kind):
                item = normalise(rec, kind, owned=False)
                if item["id"] in seen or item["id"] in related:
                    continue
                if not (item["languages"] or looks_ethiopian(item["id"])):
                    continue
                if item["downloads"] < 20 and item["likes"] < 2:
                    continue  # keep the list to things people actually use
                related[item["id"]] = item
    info(f"{len(related)} related artifacts outside the community")

    # The sweep is a discovery aid, not a catalogue. Keeping the whole tail
    # would bury the community's own work under hundreds of rows.
    RELATED_CAP = 48

    owned = sorted(seen.values(), key=lambda i: (-i["downloads"], -i["likes"], i["id"]))
    focused = [i for i in owned if i["breadth"] == "focused"]
    multilingual = [i for i in owned if i["breadth"] == "multilingual"]
    info(f"{len(focused)} built for Ethiopian languages, "
         f"{len(multilingual)} broader multilingual work a member contributed to")
    related_list = sorted(
        related.values(), key=lambda i: (-i["downloads"], -i["likes"], i["id"])
    )[:RELATED_CAP]
    if len(related) > RELATED_CAP:
        info(f"showing the top {RELATED_CAP} of {len(related)} by downloads")

    # Per-year and per-language rollups, so the templates never have to compute.
    per_year: dict[str, dict] = {}
    for item in focused:
        year = (item["created"] or "")[:4]
        if not year:
            continue
        bucket = per_year.setdefault(year, {"year": int(year), "models": 0, "datasets": 0})
        bucket["models" if item["kind"] == "model" else "datasets"] += 1

    # Focused work only. The catalogue reads this to answer "does this language
    # have a model or dataset from this community?", and a hundred-language
    # model that happens to list Amharic is not an honest yes to that question.
    per_language: dict[str, dict] = {}
    for item in focused:
        for lang in item["languages"]:
            bucket = per_language.setdefault(lang, {"name": lang, "models": 0, "datasets": 0})
            bucket["models" if item["kind"] == "model" else "datasets"] += 1

    payload = {
        "totals": {
            "models": sum(1 for i in focused if i["kind"] == "model"),
            "datasets": sum(1 for i in focused if i["kind"] == "dataset"),
            "downloads": sum(i["downloads"] for i in focused),
            "likes": sum(i["likes"] for i in focused),
            "multilingual": len(multilingual),
            "multilingual_downloads": sum(i["downloads"] for i in multilingual),
            "languages": len(per_language),
            "related": len(related_list),
        },
        "per_year": sorted(per_year.values(), key=lambda b: b["year"]),
        "per_language": sorted(per_language.values(), key=lambda b: -(b["models"] + b["datasets"])),
        "artifacts": owned,
        "related": related_list,
    }

    if args.dry_run:
        print(f"\n{payload['totals']}")
        return 0

    write_generated("huggingface.yml", payload, "sync_huggingface.py", "ecosystem_manual.yml")
    touch_meta("huggingface")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
