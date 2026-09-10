#!/usr/bin/env python3
"""Resolve one publication link to canonical metadata.

Why this exists
───────────────
The nightly sync reads OpenAlex, whose `author.display_name` is not
authoritative and is sometimes simply wrong: EMNLP 2025's homophone
normalisation paper came back with "Noam Abadi" where the ACL Anthology, and
the paper itself, say "Negasi Haile Abadi". A name is a claim about a person,
so it should come from the publisher, not from an aggregator's guess.

This module takes whatever a member pastes -- an ACL Anthology URL, a DOI, an
arXiv link, an OpenAlex or Semantic Scholar id -- and fetches the record from
the most authoritative source available for it, in this order:

    ACL Anthology .bib   the publisher's own record for an ACL venue
    Crossref             the publisher's deposited metadata for any DOI
    arXiv API            the author list as submitted
    OpenAlex / S2        last resort, and marked as such

Usage:
    python3 scripts/fetch_publication.py <url-or-id> [<url-or-id> ...]

Prints one YAML document per input, ready to paste into
_data/publications_manual.yml, plus a `source_of_record` field saying where
the metadata came from so a reviewer knows how much to trust it.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.common import clean_doi, get_json, get_text, warn  # noqa: E402

ANTHOLOGY_RE = re.compile(r"aclanthology\.org/([0-9A-Za-z.\-]+?)(?:\.pdf|/|$)")
ARXIV_RE = re.compile(r"arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5})(?:v\d+)?")
DOI_RE = re.compile(r"\b(10\.\d{4,9}/[^\s\"'<>]+)")
OPENALEX_RE = re.compile(r"openalex\.org/(W\d+)", re.I)
S2_RE = re.compile(r"semanticscholar\.org/paper/[^/]*/?([0-9a-f]{40})", re.I)


def classify(raw: str) -> tuple[str, str]:
    """(kind, identifier) for whatever the member pasted."""
    s = raw.strip()
    for pattern, kind in ((ANTHOLOGY_RE, "anthology"), (ARXIV_RE, "arxiv"),
                          (OPENALEX_RE, "openalex"), (S2_RE, "s2")):
        m = pattern.search(s)
        if m:
            return kind, m.group(1)
    m = DOI_RE.search(s)
    if m:
        doi = clean_doi(m.group(1))
        # An ACL DOI names the anthology entry, which is the better record.
        anth = re.match(r"^10\.18653/v1/(.+)$", doi or "")
        return ("anthology", anth.group(1)) if anth else ("doi", doi)
    if re.match(r"^[0-9]{4}\.[0-9]{4,5}$", s):
        return "arxiv", s
    # Bare anthology ids: modern "2025.emnlp-main.523" and legacy "P19-1001".
    if re.match(r"^\d{4}\.[a-z0-9\-]+\.\d+$", s) or re.match(r"^[A-Z]\d{2}-\d{4}$", s):
        return "anthology", s
    return "unknown", s


# ─── BibTeX ───────────────────────────────────────────────────────────────────

def bib_field(bib: str, field: str) -> str | None:
    """One field's value. The Anthology quotes with " and others with {}."""
    m = re.search(rf"\n\s*{field}\s*=\s*([{{\"])", bib, re.I)
    if not m:
        return None
    opener = m.group(1)
    i = m.end()
    if opener == "{":
        depth, out = 1, []
        while i < len(bib):
            c = bib[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if not depth:
                    break
            out.append(c)
            i += 1
    else:
        # Balance braces inside a quoted value so a brace-protected name is
        # not mistaken for the end of the field.
        depth, out = 0, []
        while i < len(bib):
            c = bib[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            elif c == '"' and depth == 0:
                break
            out.append(c)
            i += 1
    return "".join(out).strip() or None


def bib_authors(raw: str | None) -> list[str]:
    """BibTeX "Last, First and Last, First" -> ["First Last", ...]."""
    if not raw:
        return []
    names = []
    for part in re.split(r"\s+and\s+", raw.replace("\n", " ")):
        part = " ".join(part.split())
        if not part:
            continue
        if "," in part:
            last, first = part.split(",", 1)
            part = f"{first.strip()} {last.strip()}"
        part = re.sub(r"[{}\\]", "", part)
        names.append(" ".join(part.split()))
    return names


def debrace(text: str | None) -> str:
    """Strip BibTeX brace protection: "{G}e{'}ez" -> "Ge'ez"."""
    if not text:
        return ""
    return " ".join(re.sub(r"[{}]", "", text).replace("\n", " ").split())


def from_anthology(ident: str) -> dict | None:
    bib = get_text(f"https://aclanthology.org/{ident}.bib")
    if not bib:
        return None
    doi = bib_field(bib, "doi")
    return {
        "title": debrace(bib_field(bib, "title")).rstrip("."),
        "authors": [{"name": n} for n in bib_authors(bib_field(bib, "author"))],
        "year": int(bib_field(bib, "year") or 0) or None,
        "venue": debrace(bib_field(bib, "booktitle") or bib_field(bib, "journal")) or None,
        "anthology": ident,
        "doi": clean_doi(doi) if doi else f"10.18653/v1/{ident}",
        "url": f"https://aclanthology.org/{ident}/",
        "source_of_record": "ACL Anthology",
    }


def from_crossref(doi: str) -> dict | None:
    data = get_json(f"https://api.crossref.org/works/{urllib.parse.quote(doi)}")
    if not data or "message" not in data:
        return None
    m = data["message"]
    authors = []
    for a in m.get("author") or []:
        name = " ".join(x for x in (a.get("given"), a.get("family")) if x)
        if name:
            authors.append({"name": name})
    issued = (m.get("issued") or {}).get("date-parts") or [[None]]
    container = (m.get("container-title") or [None])[0]
    return {
        "title": " ".join((m.get("title") or [""])[0].split()),
        "authors": authors,
        "year": issued[0][0],
        "venue": container or (m.get("event") or {}).get("name"),
        "doi": clean_doi(m.get("DOI")),
        "url": m.get("URL"),
        "source_of_record": "Crossref",
    }


def from_arxiv(ident: str) -> dict | None:
    xml = get_text(f"http://export.arxiv.org/api/query?id_list={ident}")
    if not xml:
        return None
    import xml.etree.ElementTree as ET

    ns = {"a": "http://www.w3.org/2005/Atom"}
    entry = ET.fromstring(xml).find("a:entry", ns)
    if entry is None:
        return None
    doi = entry.findtext("{http://arxiv.org/schemas/atom}doi")
    return {
        "title": " ".join((entry.findtext("a:title", "", ns) or "").split()),
        "authors": [{"name": " ".join(n.text.split())}
                    for n in entry.findall("a:author/a:name", ns) if n.text],
        "year": int((entry.findtext("a:published", "", ns) or "0000")[:4]) or None,
        "venue": entry.findtext("{http://arxiv.org/schemas/atom}journal_ref") or "arXiv",
        "arxiv": ident,
        "doi": clean_doi(doi) if doi else f"10.48550/arXiv.{ident}",
        "url": f"https://arxiv.org/abs/{ident}",
        "source_of_record": "arXiv",
    }


def from_openalex(ident: str) -> dict | None:
    w = get_json(f"https://api.openalex.org/works/{ident}")
    if not w:
        return None
    loc = w.get("primary_location") or {}
    return {
        "title": w.get("display_name"),
        "authors": [{"name": (a.get("author") or {}).get("display_name")}
                    for a in w.get("authorships") or []
                    if (a.get("author") or {}).get("display_name")],
        "year": w.get("publication_year"),
        "venue": (loc.get("source") or {}).get("display_name"),
        "doi": clean_doi(w.get("doi")),
        "url": loc.get("landing_page_url"),
        "source_of_record": "OpenAlex (aggregator, author names not authoritative)",
    }


def resolve(raw: str) -> dict | None:
    kind, ident = classify(raw)
    if kind == "anthology":
        rec = from_anthology(ident)
        if rec:
            return rec
        warn(f"anthology {ident} not found; trying Crossref")
        return from_crossref(f"10.18653/v1/{ident}")
    if kind == "arxiv":
        return from_arxiv(ident)
    if kind == "doi":
        return from_crossref(ident)
    if kind == "openalex":
        return from_openalex(ident)
    warn(f"cannot tell what {raw!r} is")
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("links", nargs="+")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    out = []
    for raw in args.links:
        rec = resolve(raw)
        if rec:
            rec["submitted_as"] = raw
            out.append(rec)
        else:
            out.append({"submitted_as": raw, "error": "could not resolve"})

    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        import yaml
        print(yaml.safe_dump(out, allow_unicode=True, sort_keys=False, width=100))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
