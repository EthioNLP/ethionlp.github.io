#!/usr/bin/env python3
"""Turn a filled-in GitHub issue form into a file in this repository.

GitHub renders issue-form answers as a flat Markdown document:

    ### Field label

    the answer

    ### Another field

    _No response_

This script parses that back into a mapping, then dispatches on the issue's
template to write either a member file or an event file. It is the second half
of the "join by filling in a form" flow, the workflow in
.github/workflows/from-issue.yml runs it and opens a pull request with whatever
it produced.

    python3 scripts/from_issue.py --kind member --body-file issue.md
    python3 scripts/from_issue.py --kind event  --body-file issue.md

It prints the path it wrote to stdout, so the workflow can use it in the pull
request title. Anything it cannot parse is an error with a message aimed at the
person who filled in the form, not at a maintainer reading CI logs.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.common import DATA, MEMBERS_DIR, ROOT, slugify, warn  # noqa: E402
from lib.news import write_news  # noqa: E402

NO_RESPONSE = {"_no response_", "_none_", "none", "n/a", ""}

FOCUS_LABELS = {
    "datasets & corpora": "data",
    "language models": "models",
    "applications": "applications",
    "evaluation & benchmarks": "evaluation",
    "capacity building": "capacity",
    "language & linguistics": "linguistics",
}

EVENT_KINDS = {"seminar", "workshop", "conference", "tutorial", "hackathon", "reading group"}


def parse_form(body: str) -> dict[str, str]:
    """Split an issue-form body into {lowercased label: answer}."""
    fields: dict[str, str] = {}
    chunks = re.split(r"^###\s+", body.replace("\r\n", "\n"), flags=re.M)
    for chunk in chunks[1:]:
        label, _, value = chunk.partition("\n")
        value = value.strip()
        if value.lower() in NO_RESPONSE:
            continue
        fields[label.strip().lower()] = value
    return fields


def checked(value: str) -> list[str]:
    """Read the ticked items out of a checkbox field."""
    return [
        m.group(1).strip().lower()
        for m in re.finditer(r"^-\s*\[[xX]\]\s*(.+)$", value or "", re.M)
    ]


def get(fields: dict, *names: str) -> str | None:
    for name in names:
        for label, value in fields.items():
            if name in label:
                return value
    return None


# ─── Member ───────────────────────────────────────────────────────────────────

def build_member(fields: dict) -> Path:
    name = get(fields, "name")
    if not name:
        raise SystemExit("The form did not include a name, so no profile could be created.")

    urls = []
    for key in ("personal", "github", "hugging", "scholar", "orcid", "dblp", "semantic", "linkedin"):
        value = get(fields, key)
        if value:
            urls += re.findall(r"https?://\S+", value) or [value.strip()]

    focus = [FOCUS_LABELS[label] for label in checked(get(fields, "research") or "")
             if label in FOCUS_LABELS]

    cmd = [sys.executable, str(ROOT / "scripts" / "new_member.py"), *urls,
           "--name", name, "--force"]
    for flag, key in (("--role", "role"), ("--affiliation", "affiliation"),
                      ("--location", "location"), ("--bio", "about")):
        value = get(fields, key)
        if value:
            cmd += [flag, value.strip()]
    if focus:
        cmd += ["--focus", ",".join(focus)]

    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout, file=sys.stderr)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        raise SystemExit(f"Could not build a profile for {name}.")

    path = MEMBERS_DIR / f"{slugify(name)}.md"
    if not path.exists():
        raise SystemExit(f"Expected {path} to exist after scaffolding, but it does not.")

    # Membership category, from the dropdown on the form. Only `affiliate` is
    # written: plain membership is the default, and a field that says what is
    # already assumed is a field that goes stale. The category carries no
    # difference in access; see _data/membership.yml for what it does mean.
    answer = (get(fields, "which describes you", "membership") or "").lower()
    if "affiliate" in answer:
        text = path.read_text(encoding="utf-8")
        if "\nmembership:" not in text:
            text = text.replace("\n---\n", "\nmembership: affiliate\n---\n", 1)
            path.write_text(text, encoding="utf-8")

    # Best-effort identifier resolution; failure here is not fatal, because a
    # profile without publications is still a valid profile.
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "resolve_ids.py"), "--member", slugify(name)],
        capture_output=True, text=True,
    )
    return path


# ─── Event ────────────────────────────────────────────────────────────────────

def parse_date(raw: str | None, field: str) -> str:
    if not raw:
        raise SystemExit(f"The {field} field was empty. Please give a date as YYYY-MM-DD.")
    text = raw.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y", "%d %B %Y", "%B %d, %Y"):
        try:
            return dt.datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    raise SystemExit(
        f"Could not read {text!r} as a date. Please use YYYY-MM-DD, for example 2026-03-12."
    )


def yaml_str(value: str) -> str:
    value = " ".join(str(value).split())
    return '"' + value.replace('"', '\\"') + '"'


def build_event(fields: dict) -> Path:
    title = get(fields, "title")
    if not title:
        raise SystemExit("The form did not include a title, so no event could be created.")

    start = parse_date(get(fields, "date", "when"), "date")
    end = get(fields, "end date")
    end = parse_date(end, "end date") if end else None

    kind = (get(fields, "kind", "type") or "seminar").strip().lower()
    if kind not in EVENT_KINDS:
        kind = "seminar"
    kind = kind.replace(" ", "-")

    focus = [FOCUS_LABELS[label] for label in checked(get(fields, "research", "track") or "")
             if label in FOCUS_LABELS]

    speaker = get(fields, "speaker", "presenter")
    affiliation = get(fields, "affiliation")
    summary = get(fields, "summary", "abstract", "description")
    location = get(fields, "location", "where") or "Online"
    time = get(fields, "time")
    link = get(fields, "link", "url")

    lines = [
        "---",
        f"title: {yaml_str(title)}",
        f"kind: {kind}",
        f"start: {start}",
    ]
    if end:
        lines.append(f"end: {end}")
    if time:
        lines.append(f"time: {yaml_str(time)}")
    lines += [
        "timezone: EAT",
        f"location: {yaml_str(location)}",
        f"online: {'true' if 'online' in location.lower() else 'false'}",
        "status: confirmed",
    ]
    if focus:
        lines.append(f"focus: [{', '.join(focus)}]")
    if summary:
        lines.append(f"summary: {yaml_str(summary)}")
    if link:
        lines.append(f"join_url: {link.strip()}")
    if speaker:
        lines.append("speakers:")
        lines.append(f"  - name: {yaml_str(speaker)}")
        if affiliation:
            lines.append(f"    affiliation: {yaml_str(affiliation)}")
    lines.append("---")

    body = get(fields, "details", "anything else") or ""
    text = "\n".join(lines) + "\n"
    if body:
        text += "\n" + body.strip() + "\n"

    events = ROOT / "_events"
    events.mkdir(exist_ok=True)
    path = events / f"{start}-{slugify(title)[:50]}.md"
    path.write_text(text, encoding="utf-8")
    return path


# ─── Team ─────────────────────────────────────────────────────────────────────

TEAM_KINDS = {
    "research lab": "lab",
    "project or consortium": "project",
    "community or student group": "community",
    "company team": "company",
}


def org_handle(value: str | None) -> str | None:
    """Accept either a bare org name or any URL that contains one."""
    if not value:
        return None
    text = value.strip().rstrip("/")
    if not text:
        return None
    if "/" in text:
        text = text.split("/")[-1]
    return text or None


def build_team(fields: dict) -> Path:
    """Append an entry to _data/organisations.yml.

    A team is a single YAML entry rather than a file of its own: the list is
    short; it is read as one unit by both sync scripts, and keeping it in one
    place makes the ordering reviewable in a pull request.
    """
    name = get(fields, "name")
    if not name:
        raise SystemExit("The form did not include a team name.")

    hf = org_handle(get(fields, "huggingface", "hugging"))
    gh = org_handle(get(fields, "github"))
    if not hf and not gh:
        raise SystemExit(
            "A team needs a Hugging Face or a GitHub organisation, otherwise "
            "there is nothing for the sync to read."
        )

    path = DATA / "organisations.yml"
    existing = []
    if path.exists():
        with path.open(encoding="utf-8") as fh:
            existing = yaml.safe_load(fh) or []

    slug = slugify(name)
    for entry in existing:
        if entry.get("slug") == slug or (hf and entry.get("huggingface") == hf):
            raise SystemExit(f"{name} is already registered as `{entry.get('slug')}`.")

    kind = TEAM_KINDS.get((get(fields, "kind") or "").strip().lower(), "project")
    lead = get(fields, "contact person", "contact")
    lead_slug = slugify(lead) if lead else None
    # Only link a contact who is actually listed; a bare name is not a link.
    if lead_slug and not (MEMBERS_DIR / f"{lead_slug}.md").exists():
        lead_slug = None

    lines = [
        "",
        f"- name: {yaml_str(name)}",
        f"  slug: {slug}",
        f"  huggingface: {hf or ''}",
        f"  github: {gh or ''}",
        f"  website: {get(fields, 'website') or ''}",
    ]
    if get(fields, "linkedin"):
        lines.append(f"  linkedin: {get(fields, 'linkedin')}")
    if lead_slug:
        lines.append(f"  lead: {lead_slug}")
    lines += [
        f"  kind: {kind}",
        f"  joined: {dt.date.today().strftime('%Y-%m')}",
        "  summary: >-",
    ]
    summary = " ".join((get(fields, "works on", "summary") or "").split())
    lines += [f"    {summary}" if summary else "    "]

    with path.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    return path


# ─── News ─────────────────────────────────────────────────────────────────────

def build_news(fields: dict) -> Path:
    """Turn a "Share community news" issue into a draft news item."""
    title = get(fields, "headline", "title")
    if not title:
        raise SystemExit("The form did not include a headline.")

    return write_news(
        title=title,
        body=get(fields, "what happened", "body", "description") or "",
        date=get(fields, "when", "date"),
        kind=get(fields, "kind of thing", "kind"),
        link=get(fields, "link"),
        people=get(fields, "who was involved", "people"),
        source="issue",
    )


TOPIC_DIR = ROOT / "_topics"

# The form's dropdown labels, mapped to the keys _data/mentorship.yml uses.
LEVEL_LABELS = {
    "bsc project": "bsc",
    "msc thesis": "msc",
    "phd topic": "phd",
    "internship / research assistantship": "intern",
    "career & applications": "career",
}


def build_topic(fields: dict) -> Path:
    """Turn a "Post a thesis topic" issue into a file in _topics/.

    Written unpublished. A topic names a person as willing to supervise, and
    that claim gets reviewed by a maintainer before it appears on the site,
    the same rule the seeded topics follow.
    """
    title = get(fields, "title")
    if not title:
        raise SystemExit("The form did not include a title.")

    level = LEVEL_LABELS.get((get(fields, "level") or "").strip().lower(), "msc")
    area = FOCUS_LABELS.get((get(fields, "research area", "area") or "").strip().lower())

    raw_langs = get(fields, "languages") or ""
    languages = [l.strip() for l in raw_langs.split(",") if l.strip()]

    # Either a slug we can resolve, or a name we record as written. Guessing a
    # slug that does not exist would render the mentor box empty.
    mentor = (get(fields, "who would supervise it", "mentor") or "").strip()
    slug_guess = slugify(mentor)
    known = {p.stem for p in (ROOT / "_members").glob("*.md")}
    mentor_slug = slug_guess if slug_guess in known else ""

    body = get(fields, "the topic itself", "body") or ""
    stem = slugify(title)[:60] or "topic"
    path = TOPIC_DIR / f"{stem}.md"
    n = 2
    while path.exists():
        path = TOPIC_DIR / f"{stem}-{n}.md"
        n += 1

    lines = [
        "---",
        "# Submitted through the issue form and not yet reviewed. A maintainer",
        "# checks the supervision offer, fills in `mentor` if it is blank, then",
        "# deletes this comment and the `published: false` line.",
        "published: false",
        f"title: {yaml_str(title)}",
        "status: open",
        f"level: {level}",
    ]
    if area:
        lines.append(f"area: {area}")
    if languages:
        lines.append("languages: [" + ", ".join(yaml_str(l) for l in languages) + "]")
    for key, field in (("effort", "how long it would take"),
                       ("prerequisites", "what a student needs to know first")):
        value = get(fields, field, key)
        if value:
            lines.append(f"{key}: {yaml_str(value)}")
    lines.append(f"posted: {dt.date.today().isoformat()}")
    if mentor_slug:
        lines.append(f"mentor: {mentor_slug}")
    else:
        lines.append(f"# Submitted as {yaml_str(mentor)}; no matching file in _members/.")
        lines.append("mentor:")
    summary = get(fields, "one-sentence summary", "summary")
    if summary:
        lines.append("summary: >-")
        lines.append(f"  {summary.strip()}")
    lines.append("---")
    lines.append("")
    lines.append(body.strip())
    lines.append("")

    TOPIC_DIR.mkdir(exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


GALLERY_FILE = ROOT / "_data" / "gallery.yml"
IMAGE_DIR = ROOT / "resources" / "img" / "gallery"
# GitHub rewrites an attachment to one of these hosts when it is dragged into
# an issue. Anything else is somebody linking to a picture they do not control,
# which we will not copy into the repository.
ATTACHMENT_HOSTS = ("user-images.githubusercontent.com", "github.com/user-attachments")
ALLOWED = {".jpg": ".jpg", ".jpeg": ".jpg", ".png": ".png", ".webp": ".webp"}


def build_photo(fields: dict) -> Path:
    """Turn an "Add a photograph" issue into an image file and a gallery entry.

    The attachment is the point. GitHub Pages cannot receive an upload, so the
    bytes have to arrive somewhere that can: dragging a file into an issue puts
    it on GitHub's own CDN and leaves a Markdown link in the body. This fetches
    that link into the repository, so the site never depends on a URL somebody
    else can delete.
    """
    import re as _re
    import urllib.request

    caption = get(fields, "what is happening", "caption")
    if not caption:
        raise SystemExit("The form did not include a caption.")

    blob = get(fields, "the photograph", "photo") or ""
    # Stop at a quote or angle bracket as well as whitespace: pasting a file
    # into an issue can leave <img src="..."> rather than Markdown, and the
    # trailing quote was being kept as part of the URL, which then 404s.
    urls = _re.findall(r"""https?://[^\s)\]"'<>]+""", blob)
    urls = [u for u in urls if any(h in u for h in ATTACHMENT_HOSTS)]
    if not urls:
        raise SystemExit(
            "No uploaded image found. Drag the file into the form rather than "
            "pasting a link to one hosted elsewhere."
        )

    url = urls[0].rstrip(".,)\"'>")
    suffix = ALLOWED.get(Path(url.split("?")[0]).suffix.lower())
    if not suffix:
        # GitHub serves attachments without an extension often enough that this
        # has to fall back rather than fail; JPEG is the safe assumption for a
        # photograph and the browser sniffs the real type anyway.
        suffix = ".jpg"

    date = get(fields, "when", "date") or ""
    stem = _re.sub(r"[^a-z0-9]+", "-", caption.lower()).strip("-")[:48] or "photo"
    name = f"{(date[:7] + '-') if date else ''}{stem}{suffix}"
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    dest = IMAGE_DIR / name

    req = urllib.request.Request(url, headers={"User-Agent": "ethionlp.github.io"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = resp.read()
    if len(data) > 12 * 1024 * 1024:
        raise SystemExit("That image is over 12 MB; please resize it and try again.")
    dest.write_bytes(data)

    entry = ["", f"- src: /resources/img/gallery/{name}",
             f"  caption: {yaml_str(caption)}"]
    for key, *names in (("date", "when", "date"), ("place", "where", "place"),
                        ("people", "who is in it", "people"),
                        ("credit", "who took it", "credit")):
        value = get(fields, *names)
        if value:
            entry.append(f"  {key}: {yaml_str(value)}")
    with GALLERY_FILE.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(entry) + "\n")

    return dest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", required=True,
                        choices=["member", "event", "team", "news", "photo", "topic"])
    parser.add_argument("--body-file", required=True)
    parser.add_argument("--title", default="")
    args = parser.parse_args()

    body = Path(args.body_file).read_text(encoding="utf-8")
    fields = parse_form(body)
    if not fields:
        # A photo pasted straight into an issue is the one case worth rescuing:
        # the attachment is the content, and the title says what it is. Every
        # other kind needs real fields, so they still stop here.
        has_attachment = any(h in body for h in ATTACHMENT_HOSTS)
        if args.kind == "photo" and has_attachment and args.title.strip():
            fields = {"the photograph": body, "what is happening": args.title.strip()}
            warn("no form fields; using the issue title as the caption")
        else:
            raise SystemExit(
                "No form fields were found in the issue body. This workflow only "
                "understands issues created from one of the templates."
            )

    builders = {"member": build_member, "event": build_event,
                "team": build_team, "news": build_news, "photo": build_photo,
                "topic": build_topic}
    path = builders[args.kind](fields)
    print(path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
