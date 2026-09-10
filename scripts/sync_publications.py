#!/usr/bin/env python3
"""Sync community publications into _data/generated/publications.yml.

The community has many authors, so identity is per member: each ``_members/*.md``
file may declare ``orcid``, ``openalex``, ``semantic_scholar`` and ``dblp``. Any
one of them is enough to pull that member's record; declaring more improves
coverage, because no single index has everything (DBLP is best for ACL/LREC
proceedings, OpenAlex for DOIs and abstracts, Semantic Scholar for arXiv).

Records are merged by normalised title. Hand-curated entries in
``_data/publications_manual.yml`` are merged last and always win; that file is
where you fix a mangled venue string or add a dataset/model/code link.

Usage:  python3 scripts/sync_publications.py [--dry-run] [--member SLUG]
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.common import (  # noqa: E402
    CONTACT_EMAIL,
    arxiv_from_doi,
    clean_doi,
    get_json,
    get_text,
    info,
    load_curated,
    looks_ethiopian,
    member_name_index,
    norm_name,
    norm_title,
    read_members,
    squash_title,
    slugify,
    step,
    touch_meta,
    warn,
    write_generated,
)

OPENALEX = "https://api.openalex.org"
S2 = "https://api.semanticscholar.org/graph/v1"

# Venue-string hints, first match wins.
WORKSHOP_HINTS = ("workshop", "semeval", "winlp", "africanlp", "rail", "shared task", "wanlp")
PREPRINT_HINTS = ("arxiv", "corr", "preprint", "openreview", "biorxiv")


def classify(venue: str | None, work_type: str | None, doi: str | None) -> str:
    v = (venue or "").lower()
    t = (work_type or "").lower()

    if "thesis" in t or "dissertation" in t or "thesis" in v:
        return "thesis"
    if "chapter" in t:
        return "book-chapter"
    if t in ("preprint", "posted-content"):
        return "preprint"
    if any(h in v for h in PREPRINT_HINTS) and not doi:
        return "preprint"
    if any(h in v for h in WORKSHOP_HINTS):
        return "workshop"
    if t in ("article", "journal-article", "review"):
        return "journal"
    if t in ("conference-paper", "proceedings-article", "inproceedings", "conference"):
        return "conference"
    if any(h in v for h in ("proceedings", "conference", "meeting", "symposium", "coling", "acl", "lrec")):
        return "conference"
    if any(h in v for h in ("journal", "transactions")):
        return "journal"
    return "other"


def reconstruct_abstract(index: dict | None) -> str | None:
    """OpenAlex ships abstracts as an inverted index; put the words back in order."""
    if not index:
        return None
    positions = []
    for word, spots in index.items():
        positions.extend((spot, word) for spot in spots)
    if not positions:
        return None
    text = " ".join(word for _, word in sorted(positions))
    return text[:1200]


# Some sources return a few authors as "Surname, Given" while the rest of the
# same author list is "Given Surname". Left alone this both looks wrong on the
# page and stops the member matcher from recognising the name.
INVERTED_NAME = re.compile(r"^([A-Z][\w.'\-]+),\s+([A-Z][\w.'\- ]{1,40})$")


def fix_name(name: str | None) -> str | None:
    if not name:
        return name
    match = INVERTED_NAME.match(name.strip())
    return f"{match.group(2)} {match.group(1)}".strip() if match else name.strip()


# Strings the indexes sometimes return in an author slot: the affiliation line
# from a paper's header, or the publisher of the proceedings. Printed verbatim,
# they render as a co-author beside real people on their own profile pages.
NOT_A_PERSON = re.compile(
    r"\b(universit|institut(e|o|ut)?\b|laborator|department|faculty|school of"
    r"|college of|research group|language technology group|associat(ion|ed)"
    r"|society|community|press\b|publish|gmbh|ltd\b|inc\.|llc\b)",
    re.I,
)


def is_person(name: str | None) -> bool:
    """False for an organisation or an affiliation line in an author slot."""
    if not name or not name.strip():
        return False
    return not NOT_A_PERSON.search(name)


def blank(title: str) -> dict:
    return {
        "key": slugify(title)[:80],
        "title": title,
        "authors": [],
        "year": None,
        "venue": None,
        "type": "other",
        "doi": None,
        "url": None,
        "arxiv": None,
        "anthology": None,
        "code": None,
        "dataset": None,
        "model": None,
        "abstract": None,
        "members": [],
        "sources": [],
        "ethiopian": False,
    }


def merge(into: dict, other: dict) -> None:
    """Fill gaps in ``into`` from ``other`` without overwriting what is there."""
    for field in ("year", "venue", "doi", "url", "arxiv", "anthology", "abstract",
                  "code", "dataset", "model"):
        if not into.get(field) and other.get(field):
            into[field] = other[field]

    # Prefer the longer author list: partial lists are the usual failure mode.
    if len(other.get("authors") or []) > len(into.get("authors") or []):
        into["authors"] = other["authors"]

    if into["type"] in ("other", None) and other.get("type") not in (None, "other"):
        into["type"] = other["type"]

    for source in other.get("sources", []):
        if source not in into["sources"]:
            into["sources"].append(source)


def anthology_id(url: str | None) -> str | None:
    if not url:
        return None
    match = re.search(r"aclanthology\.org/([^/?#]+)", url)
    return match.group(1).rstrip("/") if match else None


# ─── Sources ──────────────────────────────────────────────────────────────────

def from_openalex(author_id: str) -> list[dict]:
    out, cursor = [], "*"
    while cursor and len(out) < 500:
        url = (
            f"{OPENALEX}/works?filter=author.id:{author_id}"
            f"&per-page=200&cursor={cursor}&mailto={CONTACT_EMAIL}"
        )
        page = get_json(url)
        if not page:
            break
        for work in page.get("results", []):
            title = (work.get("display_name") or "").strip()
            if not title:
                continue
            rec = blank(title)
            rec["year"] = work.get("publication_year")
            location = work.get("primary_location") or {}
            source = location.get("source") or {}
            rec["venue"] = source.get("display_name")
            rec["doi"] = clean_doi(work.get("doi"))
            rec["url"] = location.get("landing_page_url") or (
                f"https://doi.org/{rec['doi']}" if rec["doi"] else None
            )
            rec["anthology"] = anthology_id(rec["url"])
            rec["abstract"] = reconstruct_abstract(work.get("abstract_inverted_index"))
            rec["type"] = classify(rec["venue"], work.get("type"), rec["doi"])
            rec["authors"] = [
                {"name": (a.get("author") or {}).get("display_name")}
                for a in work.get("authorships", [])
                if is_person((a.get("author") or {}).get("display_name"))
            ]
            for loc in work.get("locations", []) or []:
                landing = (loc or {}).get("landing_page_url") or ""
                if "arxiv.org" in landing:
                    match = re.search(r"arxiv\.org/abs/([\d.]+)", landing)
                    if match:
                        rec["arxiv"] = match.group(1)
                if not rec["anthology"]:
                    rec["anthology"] = anthology_id(landing)
            rec["sources"] = ["openalex"]
            out.append(rec)
        cursor = (page.get("meta") or {}).get("next_cursor")
    return out


def from_semantic_scholar(author_id: str) -> list[dict]:
    fields = "title,year,venue,externalIds,abstract,publicationTypes,authors,url"
    data = get_json(f"{S2}/author/{author_id}/papers?fields={fields}&limit=500")
    if not data:
        return []
    out = []
    for paper in data.get("data", []):
        title = (paper.get("title") or "").strip()
        if not title:
            continue
        ext = paper.get("externalIds") or {}
        rec = blank(title)
        rec["year"] = paper.get("year")
        rec["venue"] = paper.get("venue") or None
        rec["doi"] = clean_doi(ext.get("DOI"))
        rec["arxiv"] = ext.get("ArXiv")
        rec["anthology"] = ext.get("ACL")
        rec["url"] = (
            f"https://aclanthology.org/{ext['ACL']}/" if ext.get("ACL")
            else f"https://doi.org/{rec['doi']}" if rec["doi"]
            else f"https://arxiv.org/abs/{rec['arxiv']}" if rec["arxiv"]
            else paper.get("url")
        )
        rec["abstract"] = (paper.get("abstract") or None)
        types = paper.get("publicationTypes") or []
        rec["type"] = classify(rec["venue"], types[0] if types else None, rec["doi"])
        rec["authors"] = [{"name": a.get("name")} for a in paper.get("authors", [])
                          if is_person(a.get("name"))]
        rec["sources"] = ["semantic_scholar"]
        out.append(rec)
    return out


def from_dblp(pid: str) -> list[dict]:
    xml = get_text(f"https://dblp.org/pid/{pid}.xml")
    if not xml:
        return []
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as exc:
        warn(f"dblp {pid}: {exc}")
        return []

    out = []
    for entry in root.iter():
        if entry.tag not in ("article", "inproceedings", "incollection", "phdthesis", "mastersthesis"):
            continue
        title = "".join(entry.find("title").itertext()).strip().rstrip(".") if entry.find("title") is not None else ""
        if not title:
            continue
        rec = blank(title)
        year_el = entry.find("year")
        rec["year"] = int(year_el.text) if year_el is not None and year_el.text else None
        venue_el = entry.find("booktitle") if entry.find("booktitle") is not None else entry.find("journal")
        rec["venue"] = venue_el.text if venue_el is not None else None
        for ee in entry.findall("ee"):
            if ee.text and "doi.org" in ee.text:
                rec["doi"] = clean_doi(ee.text)
            if ee.text and not rec["url"]:
                rec["url"] = ee.text
        rec["anthology"] = anthology_id(rec["url"])
        rec["type"] = classify(rec["venue"], entry.tag, rec["doi"])
        rec["authors"] = [{"name": a.text} for a in entry.findall("author")
                          if is_person(a.text)]
        rec["sources"] = ["dblp"]
        out.append(rec)
    return out


def resolve_openalex(member: dict) -> str | None:
    """An explicit OpenAlex id wins; otherwise resolve the ORCID."""
    explicit = (member.get("openalex") or "").strip()
    if explicit:
        return explicit.rstrip("/").split("/")[-1]

    orcid = (member.get("orcid") or "").strip()
    if not orcid:
        return None
    orcid = orcid.rstrip("/").split("/")[-1]
    author = get_json(f"{OPENALEX}/authors/orcid:{orcid}?mailto={CONTACT_EMAIL}")
    if not author:
        warn(f"could not resolve ORCID {orcid}")
        return None
    return (author.get("id") or "").rstrip("/").split("/")[-1]


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--member", help="sync a single member by slug")
    args = parser.parse_args()

    members = read_members()
    if args.member:
        members = [m for m in members if m["slug"] == args.member]
        if not members:
            warn(f"no member with slug {args.member!r}")
            return 1

    name_index = member_name_index(read_members())
    # Papers a merged author identifier drags in that this community did not
    # write. See _data/publications_exclude.yml for why each one is listed.
    _exclusions = load_curated("publications_exclude.yml") or []
    excluded = {clean_doi(e["doi"]) for e in _exclusions if e.get("doi")}
    excluded.discard(None)
    # Some of what a merged identifier drags in has no DOI at all -- a
    # proceedings front matter, a table of contents, somebody's CV -- so titles
    # are matchable too, on the same normalisation the deduplication uses.
    excluded_titles = {norm_title(e["title"]) for e in _exclusions if e.get("title")}
    excluded_titles.discard("")
    if excluded or excluded_titles:
        info(f"exclusion list: {len(excluded)} DOI(s), "
             f"{len(excluded_titles)} title(s)")
    merged: dict[str, dict] = {}
    # doi -> the key in `merged` that already holds that DOI. Title matching
    # alone left duplicates behind whenever two sources punctuated, subtitled
    # or truncated the same paper differently; a shared DOI is the one signal
    # that says "same paper" regardless of how it is spelled.
    by_doi: dict[str, str] = {}
    # arxiv id -> key, for the other duplicate shape: the same paper held once
    # as a preprint and once as the published version. Those carry different
    # DOIs by definition, and their titles often differ too because the arXiv
    # v1 title was revised before publication ("...for 14 Languages" against
    # "...for 13 Languages"). The arXiv id is the same in both.
    by_arxiv: dict[str, str] = {}
    # squashed title -> key, for the same paper hyphenated differently by two
    # sources. Checked last, after both identifier keys.
    by_squash: dict[str, str] = {}
    identified = 0

    for member in members:
        ids = []
        oa = resolve_openalex(member)
        if oa:
            ids.append(("openalex", oa))
        if member.get("semantic_scholar"):
            ids.append(("semantic_scholar", str(member["semantic_scholar"]).strip()))
        if member.get("dblp"):
            ids.append(("dblp", str(member["dblp"]).strip().replace("https://dblp.org/pid/", "").rstrip("/")))

        if not ids:
            continue
        identified += 1
        step(f"{member['name']} ({', '.join(k for k, _ in ids)})")

        records = []
        for kind, value in ids:
            if kind == "openalex":
                records += from_openalex(value)
            elif kind == "semantic_scholar":
                records += from_semantic_scholar(value)
            elif kind == "dblp":
                records += from_dblp(value)

        for rec in records:
            key = norm_title(rec["title"])
            if not key:
                continue
            doi = clean_doi(rec.get("doi"))
            if (doi and doi in excluded) or key in excluded_titles:
                continue
            # An arXiv DOI carries the same identity as the arxiv field, so
            # normalise it across: otherwise one source's record holds the id
            # in `doi` and another's in `arxiv`, and they never meet.
            arxiv = (rec.get("arxiv") or "").strip() or arxiv_from_doi(doi)
            if arxiv and not rec.get("arxiv"):
                rec["arxiv"] = arxiv
            squash = squash_title(rec["title"])
            # A DOI, arXiv id or squashed title already seen under a different
            # normalised title wins: merge into the record that holds it rather
            # than opening a second entry.
            if doi and doi in by_doi and by_doi[doi] != key:
                key = by_doi[doi]
            elif arxiv and arxiv in by_arxiv and by_arxiv[arxiv] != key:
                key = by_arxiv[arxiv]
            elif squash in by_squash and by_squash[squash] != key:
                key = by_squash[squash]
            if key in merged:
                merge(merged[key], rec)
            else:
                merged[key] = rec
            if doi:
                by_doi.setdefault(doi, key)
            if arxiv:
                by_arxiv.setdefault(arxiv, key)
            by_squash.setdefault(squash, key)
            if member["slug"] not in merged[key]["members"]:
                merged[key]["members"].append(member["slug"])

        info(f"{len(records)} raw records")

    if not identified:
        warn(
            "no member declares orcid / openalex / semantic_scholar / dblp, "
            "nothing to sync. Add one of those keys to a file in _members/."
        )

    step("Curated entries (_data/publications_manual.yml)")
    curated = load_curated("publications_manual.yml") or []
    for entry in curated:
        title = (entry.get("title") or "").strip()
        if not title:
            continue
        key = norm_title(title)
        rec = merged.get(key) or blank(title)
        # Curated values win outright; that is the point of the file.
        for field, value in entry.items():
            if value not in (None, "", []):
                rec[field] = value
        rec["title"] = title
        rec.setdefault("members", [])
        if "curated" not in rec.get("sources", []):
            rec.setdefault("sources", []).append("curated")
        merged[key] = rec
    info(f"{len(curated)} curated")

    step("Post-processing")
    for rec in merged.values():
        # Mark which listed authors are community members, so the templates can
        # bold them and link to profiles.
        for author in rec.get("authors") or []:
            author["name"] = fix_name(author.get("name"))
            slug = name_index.get(norm_name(author.get("name") or ""))
            if slug:
                author["member"] = slug
                if slug not in rec["members"]:
                    rec["members"].append(slug)

        rec["ethiopian"] = bool(
            looks_ethiopian(rec.get("title") or "", rec.get("abstract") or "", rec.get("venue") or "")
        )
        if not rec.get("url") and rec.get("anthology"):
            rec["url"] = f"https://aclanthology.org/{rec['anthology']}/"
        if not rec.get("url") and rec.get("arxiv"):
            rec["url"] = f"https://arxiv.org/abs/{rec['arxiv']}"
        rec["author_line"] = ", ".join(a.get("name") or "" for a in rec.get("authors") or [])

    records = sorted(
        merged.values(),
        key=lambda r: (-(r.get("year") or 0), (r.get("title") or "").lower()),
    )

    by_year: dict[int, int] = {}
    by_type: dict[str, int] = {}
    for rec in records:
        if rec.get("year"):
            by_year[rec["year"]] = by_year.get(rec["year"], 0) + 1
        by_type[rec["type"]] = by_type.get(rec["type"], 0) + 1

    payload = {
        "totals": {
            "publications": len(records),
            "ethiopian": sum(1 for r in records if r["ethiopian"]),
            "members_covered": identified,
            "years": sorted(by_year.keys(), reverse=True),
        },
        "by_year": [{"year": y, "count": c} for y, c in sorted(by_year.items())],
        "by_type": [{"type": t, "count": c} for t, c in sorted(by_type.items(), key=lambda i: -i[1])],
        "publications": records,
    }

    if args.dry_run:
        print(f"\n{payload['totals']}")
        return 0

    write_generated("publications.yml", payload, "sync_publications.py", "publications_manual.yml")
    touch_meta("publications")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
