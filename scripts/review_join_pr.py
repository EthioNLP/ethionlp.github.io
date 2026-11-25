#!/usr/bin/env python3
"""Post an advisory review on a pull request built from a "Join EthioNLP" issue.

The issue-to-PR workflow turns the join form into `_members/<slug>.md`. This
script compares that file with the form it came from and leaves one comment on
the pull request saying whether it looks ready for a maintainer, plus specific
questions for the person who joined when something does not line up.

It is advisory only. It never approves, requests changes or merges; it cannot
verify who someone is or that they agreed to be listed beyond the form's
checkboxes. It only reads the pull request through the API, so no code from
the pull request ever runs with the workflow's token.

    # in CI (GITHUB_TOKEN and GITHUB_REPOSITORY set)
    python3 scripts/review_join_pr.py --issue 90
    python3 scripts/review_join_pr.py --pr 91

    # locally, against files on disk, printing the comment
    python3 scripts/review_join_pr.py --body-file issue.md --profile _members/x.md
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from from_issue import FOCUS_LABELS, checked, get, membership_category, parse_form  # noqa: E402
from lib.common import slugify  # noqa: E402

MARKER = "<!-- ethionlp-join-review -->"
BRANCH = re.compile(r"^contrib/issue-(\d+)$")

# Keys new_member.py and resolve_ids.py write for a form submission. Anything
# else in the file was added by hand and is worth a maintainer's look.
GENERATED_KEYS = {
    "name", "title", "role", "affiliation", "location", "photo", "order", "focus",
    "website", "github", "huggingface", "scholar", "orcid", "semantic_scholar",
    "dblp", "linkedin", "twitter", "membership", "openalex",
}

TEXT_FIELDS = (
    # (profile key, form label substrings, how to name it to a person)
    ("role", ("role",), "role"),
    ("affiliation", ("affiliation",), "affiliation"),
    ("location", ("location", "where you are based"), "location"),
)

CONSENT_ITEMS = (
    ("public website", "that you are happy for this information to appear on a public website"),
    ("community standards", "that you have read and agree to the community standards"),
)


# ─── Identifiers ──────────────────────────────────────────────────────────────

def _bare(value: str) -> str | None:
    bare = value.strip().lstrip("@").strip("/")
    return bare if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", bare) else None


def _host_handle(host: str, value: str) -> str | None:
    match = re.search(host + r"/([^/?#\s]+)", value, re.I)
    if match:
        return match.group(1).lower()
    if "://" in value or "/" in value.strip().strip("/"):
        return None
    bare = _bare(value)
    return bare.lower() if bare else None


def github_id(value: str) -> str | None:
    return _host_handle(r"github\.com", value)


def huggingface_id(value: str) -> str | None:
    return _host_handle(r"huggingface\.co", value)


def orcid_id(value: str) -> str | None:
    match = re.search(r"(\d{4}-\d{4}-\d{4}-\d{3}[\dXx])", value)
    return match.group(1).upper() if match else None


def orcid_checksum_ok(orcid: str) -> bool:
    """ISO 7064 MOD 11-2, the check digit every ORCID ends with."""
    digits = orcid.replace("-", "")
    total = 0
    for ch in digits[:-1]:
        total = (total + int(ch)) * 2
    check = (12 - total % 11) % 11
    return digits[-1] == ("X" if check == 10 else str(check))


def scholar_id(value: str) -> str | None:
    match = re.search(r"[?&]user=([\w-]+)", value)
    return match.group(1) if match else None


def linkedin_id(value: str) -> str | None:
    match = re.search(r"linkedin\.com/in/([^/?#\s]+)", value, re.I)
    return urllib.parse.unquote(match.group(1)).lower() if match else None


def website_id(value: str) -> str | None:
    value = value.strip()
    match = re.search(r"https?://\S+", value)
    if match:
        value = match.group(0)
    elif "." not in value or " " in value:
        return None
    value = re.sub(r"^https?://", "", value, flags=re.I)
    host, _, rest = value.partition("/")
    host = host.lower().removeprefix("www.")
    return (host + ("/" + rest if rest else "")).rstrip("/")


LINK_FIELDS = (
    # (profile key, form label substring, display name, parser)
    ("github", "github", "GitHub", github_id),
    ("huggingface", "hugging", "Hugging Face", huggingface_id),
    ("scholar", "scholar", "Google Scholar", scholar_id),
    ("orcid", "orcid", "ORCID", orcid_id),
    ("website", "personal", "personal site", website_id),
    ("linkedin", "linkedin", "LinkedIn", linkedin_id),
)


# ─── Review ───────────────────────────────────────────────────────────────────

@dataclass
class ChangedFile:
    path: str
    status: str = "added"  # as the pull request files API reports it


@dataclass
class Review:
    questions: list[str] = field(default_factory=list)  # for the person joining
    checks: list[str] = field(default_factory=list)     # for a maintainer
    notes: list[str] = field(default_factory=list)      # informational only

    @property
    def status(self) -> str:
        if self.questions:
            return "clarify"
        if self.checks:
            return "maintainer"
        return "ready"


def squash(value) -> str:
    return " ".join(str(value or "").split())


def split_profile(text: str) -> tuple[dict | None, str]:
    match = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)(.*)$", text, re.S)
    if not match:
        return None, ""
    try:
        data = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return None, ""
    if not isinstance(data, dict):
        return None, ""
    return data, match.group(2).strip()


def is_join_issue(body: str, labels: list[str]) -> bool:
    if any("join" in label.lower() for label in labels):
        return True
    return "### Full name" in body and "### Which describes you?" in body


def review(
    issue_body: str,
    files: list[ChangedFile],
    profile_text: str | None,
    issue_author: str = "",
    openalex_orcid=None,
) -> Review:
    """Compare the proposed profile with the join form it was built from.

    `openalex_orcid(author_id)` returns the ORCID on an OpenAlex author record,
    or None when there is none or it cannot be fetched.
    """
    result = Review()
    q, chk, note = result.questions.append, result.checks.append, result.notes.append

    members = [f for f in files if f.path.startswith("_members/") and f.path.endswith(".md")]
    others = [f.path for f in files if f not in members]
    if others:
        chk("This pull request also changes files other than the profile: "
            + ", ".join(f"`{p}`" for p in others) + ". A join request should only add one profile.")
    if len(members) != 1:
        chk(f"Expected exactly one profile under `_members/`, found {len(members)}.")
        return result
    profile_file = members[0]
    if profile_file.status == "removed":
        chk(f"`{profile_file.path}` is deleted by this pull request, not added.")
        return result
    if profile_file.status == "modified":
        chk(f"`{profile_file.path}` already exists, and this pull request replaces it. "
            "Please confirm it is the same person and nothing curated is lost.")

    profile, bio = split_profile(profile_text or "")
    if profile is None:
        chk(f"`{profile_file.path}` does not start with valid YAML front matter, so the site cannot read it.")
        return result

    fields = parse_form(issue_body or "")
    if not fields:
        q("The issue does not look like the Join EthioNLP form, so there was nothing to compare the profile with. "
          "Could you fill in the form from https://github.com/EthioNLP/ethionlp.github.io/issues/new/choose instead?")
        return result

    # Name.
    form_name = squash(get(fields, "name"))
    if not form_name:
        q("The form has no full name. What name should appear on your profile?")
    elif squash(profile.get("name")) != form_name:
        q(f"The form gives your name as **{form_name}**, but the profile says "
          f"**{squash(profile.get('name')) or '(nothing)'}**. Which spelling is right? "
          "If the form is wrong, please edit it so the two match.")
    if squash(profile.get("title")) != squash(profile.get("name")):
        chk("The profile's `title` and `name` differ; they should be the same.")
    if profile.get("name") and Path(profile_file.path).stem != slugify(str(profile["name"])):
        note(f"The file name `{profile_file.path}` does not match the name, which only affects the page address.")

    # Free text fields.
    for key, labels, display in TEXT_FIELDS:
        given = squash(get(fields, *labels))
        shown = squash(profile.get(key))
        if given and shown != given:
            q(f"You wrote **{given}** as your {display}, but the profile shows "
              f"**{shown or '(nothing)'}**. Which should appear?")
        elif shown and not given:
            q(f"The profile shows **{shown}** as your {display}, which was not on the form "
              "(it may have been copied from a linked public profile). Should it be shown?")

    about = squash(get(fields, "about"))
    if about and squash(bio) != about:
        q("The description on your profile is different from the one you wrote on the form. "
          "Which one should appear?")
    elif bio and not about:
        q("The profile includes a description you did not write on the form "
          f"(it may be a GitHub bio): \u201c{squash(bio)[:200]}\u201d. Should it appear on your profile?")

    # Links.
    for key, label, display, parse in LINK_FIELDS:
        raw = get(fields, label)
        shown_raw = profile.get(key)
        shown = parse(str(shown_raw)) if shown_raw else None
        if raw:
            given = parse(raw)
            if not given:
                q(f"The {display} field says \u201c{squash(raw)}\u201d, which could not be read as a "
                  f"{display} link, so it was left off. What is the correct link?")
                continue
            if key == "orcid" and not orcid_checksum_ok(given):
                q(f"The ORCID **{given}** has an invalid check digit, so it is probably mistyped. "
                  "Could you copy it again from https://orcid.org?")
            if shown != given:
                q(f"You gave **{squash(raw)}** for {display}, but the profile has "
                  f"**{squash(shown_raw) or '(nothing)'}**. Which is right?")
        elif shown_raw and key == "orcid":
            q(f"The profile lists ORCID **{squash(shown_raw)}**, which you did not give on the form; "
              "it was matched automatically by name. Is https://orcid.org/"
              f"{squash(shown_raw)} yours? If not, say so and it will be removed.")
        elif shown_raw:
            q(f"The profile links a {display} (**{squash(shown_raw)}**) that was not in the form's {display} "
              "field. Is it yours, and should it be shown?")

    if profile.get("twitter"):
        q(f"The profile links an X/Twitter account (**{squash(profile['twitter'])}**) that was not on the form "
          "(it may have been copied from your GitHub profile). Should it be shown?")
    for key in ("semantic_scholar", "dblp"):
        if profile.get(key):
            chk(f"`{key}` is set, but the form has no field for it, so it was added by hand. Please confirm it.")
    if profile.get("photo"):
        note("The profile photo is the public avatar from the linked GitHub or Hugging Face account.")

    # Author identity: OpenAlex ids come from a name search, and names are shared.
    openalex = squash(profile.get("openalex"))
    if openalex:
        form_orcid = orcid_id(get(fields, "orcid") or "")
        record_orcid = openalex_orcid(openalex) if (openalex_orcid and form_orcid) else None
        record_orcid = orcid_id(record_orcid or "")
        if form_orcid and record_orcid == form_orcid:
            note(f"The OpenAlex author [{openalex}](https://openalex.org/{openalex}) lists the same ORCID "
                 "given on the form, so the match is consistent. It was still found by name, so a quick "
                 "look at the papers is worthwhile.")
        else:
            q(f"Your papers will be pulled from the OpenAlex author [{openalex}](https://openalex.org/{openalex}), "
              "which was matched by name only. Is that you? If it is not, say so and it will be removed. "
              "Adding your ORCID to the form makes this match exact.")

    # Membership.
    answer = get(fields, "which describes you", "membership")
    if not answer:
        q("The form does not say which membership category describes you. "
          "Could you pick one under \u201cWhich describes you?\u201d?")
    else:
        expected = membership_category(answer)
        if expected is None and "member" not in answer.lower():
            q(f"The membership answer \u201c{squash(answer)}\u201d is not one of the form's options. "
              "Which category describes you?")
        elif squash(profile.get("membership")) != (expected or ""):
            q(f"You chose \u201c{squash(answer)}\u201d, but the profile's membership is "
              f"**{profile.get('membership') or 'member'}**. Which is right?")

    # Research tracks.
    tracks = get(fields, "research")
    expected_focus = {FOCUS_LABELS[t] for t in checked(tracks or "") if t in FOCUS_LABELS}
    shown_focus = set(profile.get("focus") or [])
    if expected_focus != shown_focus:
        q("The research tracks on the profile ("
          + (", ".join(sorted(shown_focus)) or "none")
          + ") are not the ones ticked on the form ("
          + (", ".join(sorted(expected_focus)) or "none")
          + "). Which tracks should be listed?")

    # Consent. The form requires both boxes, but an edited issue can untick them.
    ticked = set(checked(get(fields, "confirmation") or ""))
    required_labels = {
        "public website": (
            "I am happy for this information to appear on a public website, and I understand "
            "it lives in a public Git repository that I can edit or remove at any time."
        ).lower(),
        "community standards": (
            "I have read the community standards at https://ethionlp.github.io/standards/ "
            "and agree to them, including the rules for posting in the Telegram and Discord groups."
        ).lower(),
    }
    for needle, what in CONSENT_ITEMS:
        if required_labels[needle] not in ticked:
            q(f"The form does not confirm {what}. Please tick that box in the issue; "
              "the profile cannot be published without it.")

    # Someone adding a colleague is allowed, but that person should know.
    handle = github_id(get(fields, "github") or "")
    if handle and issue_author and handle != issue_author.lower():
        q(f"This was submitted by @{issue_author} for the GitHub account **{handle}**. If you are adding "
          "someone else, please confirm they have agreed to be listed.")

    extra = sorted(k for k in profile if k not in GENERATED_KEYS)
    if extra:
        chk("The profile sets " + ", ".join(f"`{k}`" for k in extra)
            + ", which the form never produces. Please confirm these were meant to be added.")
    if profile.get("order") not in (None, 900):
        chk(f"`order: {profile.get('order')}` differs from the default 900 for new members.")

    return result


# ─── Comment ──────────────────────────────────────────────────────────────────

HEADINGS = {
    "ready": "\u2705 Looks ready for a maintainer",
    "clarify": "\u2753 Needs clarification",
    "maintainer": "\U0001F440 Needs a maintainer check",
}


def render(result: Review, issue_number: int | None, author: str = "",
           profile_path: str = "", sha: str = "") -> str:
    issue = f"#{issue_number}" if issue_number else "the join issue"
    lines = [MARKER, f"### Join request review: {HEADINGS[result.status]}", ""]

    if result.status == "ready":
        lines.append("The proposed profile matches the form, and both confirmations are ticked. "
                     "Nothing here needs clarifying, so this looks ready for a maintainer to approve.")
    elif result.status == "clarify":
        who = f"@{author}, thank" if author else "Thank"
        lines.append(f"{who} you for joining! Before a maintainer approves this, could you help with the "
                     f"questions below? The easiest way is to edit the form in {issue}: this pull request "
                     "and this review update by themselves. You can also reply here.")
    else:
        lines.append("The profile matches the form, but something below needs a maintainer to look at it.")

    for title, items, numbered in (("Questions", result.questions, True),
                                   ("For maintainers", result.checks, False),
                                   ("Notes", result.notes, False)):
        if not items:
            continue
        lines += ["", f"**{title}**", ""]
        lines += [f"{i}. {text}" if numbered else f"- {text}" for i, text in enumerate(items, 1)]

    target = f"`{profile_path}`" if profile_path else "the proposed profile"
    at = f" at {sha[:7]}" if sha else ""
    lines += [
        "",
        f"<sub>Automated advisory review comparing {target}{at} with {issue}. It does not verify "
        "anyone's identity or consent beyond what the form says, and it never approves or merges. "
        "A maintainer makes the final call.</sub>",
    ]
    return "\n".join(lines) + "\n"


# ─── GitHub ───────────────────────────────────────────────────────────────────

class GitHub:
    def __init__(self, repo: str, token: str, api: str = "https://api.github.com"):
        self.repo, self.token, self.api = repo, token, api.rstrip("/")

    def call(self, method: str, path: str, payload: dict | None = None):
        url = path if path.startswith("http") else f"{self.api}{path}"
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(url, data=data, method=method, headers={
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ethionlp-join-review",
        })
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read()
            return json.loads(body) if body else None

    def paged(self, path: str) -> list:
        items, page = [], 1
        sep = "&" if "?" in path else "?"
        while True:
            batch = self.call("GET", f"{path}{sep}per_page=100&page={page}") or []
            items += batch
            if len(batch) < 100:
                return items
            page += 1

    def repo_path(self, suffix: str) -> str:
        return f"/repos/{self.repo}{suffix}"


def fetch_openalex_orcid(author_id: str) -> str | None:
    url = f"https://api.openalex.org/authors/{urllib.parse.quote(author_id)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ethionlp-join-review"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return (json.loads(resp.read()) or {}).get("orcid")
    except (urllib.error.URLError, ValueError, TimeoutError):
        return None


def upsert_comment(gh: GitHub, pr_number: int, body: str) -> str:
    """Keep exactly one review comment from a bot on the pull request."""
    mine = [c for c in gh.paged(gh.repo_path(f"/issues/{pr_number}/comments"))
            if (c.get("user") or {}).get("type") == "Bot" and MARKER in (c.get("body") or "")]
    for extra in mine[1:]:
        gh.call("DELETE", gh.repo_path(f"/issues/comments/{extra['id']}"))
    if not mine:
        gh.call("POST", gh.repo_path(f"/issues/{pr_number}/comments"), {"body": body})
        return "created"
    if mine[0].get("body") == body:
        return "unchanged"
    gh.call("PATCH", gh.repo_path(f"/issues/comments/{mine[0]['id']}"), {"body": body})
    return "updated"


def review_pull_request(gh: GitHub, pr: dict, dry_run: bool = False) -> int:
    number = pr["number"]
    head = pr.get("head") or {}
    branch = BRANCH.match(head.get("ref") or "")
    if pr.get("state") != "open" or not branch or (head.get("repo") or {}).get("full_name") != gh.repo:
        print(f"#{number} is not an open join pull request from this repository; skipping.")
        return 0

    issue_number = int(branch.group(1))
    issue = gh.call("GET", gh.repo_path(f"/issues/{issue_number}"))
    body = issue.get("body") or ""
    labels = [label.get("name", "") for label in issue.get("labels") or []]
    if issue.get("pull_request") or not is_join_issue(body, labels):
        print(f"#{issue_number} is not a join request; skipping.")
        return 0

    files = [ChangedFile(f["filename"], f.get("status", "added"))
             for f in gh.paged(gh.repo_path(f"/pulls/{number}/files"))]
    members = [f for f in files if f.path.startswith("_members/") and f.path.endswith(".md")]
    if not members:
        print(f"#{number} does not change a member profile; skipping.")
        return 0

    profile_text = None
    if len(members) == 1 and members[0].status != "removed":
        # Read as data through the API. The pull request is never checked out.
        quoted = urllib.parse.quote(members[0].path)
        content = gh.call("GET", gh.repo_path(f"/contents/{quoted}?ref={head['sha']}"))
        profile_text = base64.b64decode(content["content"]).decode("utf-8")

    author = (issue.get("user") or {}).get("login", "")
    result = review(body, files, profile_text, author, fetch_openalex_orcid)
    comment = render(result, issue_number, author, members[0].path, head.get("sha", ""))
    if dry_run:
        print(comment)
        return 0
    outcome = upsert_comment(gh, number, comment)
    print(f"#{number}: {result.status}, comment {outcome}.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--pr", type=int, help="pull request number")
    target.add_argument("--issue", type=int, help="join issue number; reviews its open pull request")
    target.add_argument("--body-file", help="offline: the issue body as Markdown")
    parser.add_argument("--profile", help="offline: the proposed _members/*.md file")
    parser.add_argument("--author", default="", help="offline: who opened the issue")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--dry-run", action="store_true", help="print the comment instead of posting it")
    args = parser.parse_args()

    if args.body_file:
        if not args.profile:
            parser.error("--body-file needs --profile")
        path = Path(args.profile)
        rel = f"_members/{path.name}"
        result = review(Path(args.body_file).read_text(encoding="utf-8"), [ChangedFile(rel)],
                        path.read_text(encoding="utf-8"), args.author, fetch_openalex_orcid)
        print(render(result, None, args.author, rel))
        return 0

    token = os.environ.get("GITHUB_TOKEN")
    if not token or not args.repo:
        parser.error("set GITHUB_TOKEN and GITHUB_REPOSITORY (or --repo)")
    gh = GitHub(args.repo, token)

    if args.issue:
        owner = args.repo.split("/")[0]
        head = urllib.parse.quote(f"{owner}:contrib/issue-{args.issue}")
        pulls = gh.call("GET", gh.repo_path(f"/pulls?state=open&head={head}"))
        if not pulls:
            print(f"No open pull request for #{args.issue}; nothing to review.")
            return 0
        pr = pulls[0]
    else:
        pr = gh.call("GET", gh.repo_path(f"/pulls/{args.pr}"))
    return review_pull_request(gh, pr, args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
