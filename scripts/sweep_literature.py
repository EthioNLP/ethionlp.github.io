#!/usr/bin/env python3
"""Find work on Ethiopian languages published by people who are not members.

sync_publications.py works outward from the people: it takes each member's
ORCID, OpenAlex, DBLP or Semantic Scholar id and collects what they published.
That is the right way to build a member's page, and it is blind by design to
everyone outside the directory.

This works the other way round: it searches the literature by subject, and then
subtracts the members. What is left is the field as it exists beyond this
community, which is most of it. It answers two questions the site could not
answer before, "who else works on these languages" and "what have they built".

SOURCES

  OpenAlex            primary. No key, no rate limit worth the name, and it
                      ingests Crossref, DBLP, PubMed and arXiv, so ACL
                      Anthology, IEEE, AAAI, Springer and Elsevier papers all
                      arrive through it rather than needing separate clients.
  Semantic Scholar    a second opinion. Its coverage of NLP venues is good and
                      it disagrees with OpenAlex often enough to be worth the
                      call. Unauthenticated, so it is rate limited and may
                      simply refuse; that is survivable and the run says so.
  ACL Anthology       reached through both of the above, which carry Anthology
                      ids and DOIs. Its own bibliography is a 200MB BibTeX
                      dump, and re-deriving from it what OpenAlex already has
                      indexed would add nothing.

  IEEE Xplore and AAAI have no free API: IEEE's needs a paid subscription key
  and AAAI publishes no API at all. Both deposit DOIs with Crossref, so their
  papers reach us through OpenAlex; anything they do not deposit is invisible
  here, and the page says so rather than implying completeness.

PRECISION

  Two gates, because a search for a language name alone is mostly noise. A work
  is kept only if it matches a language or country term AND an NLP term, both
  in the title or abstract. The terms are listed below and are meant to be
  edited: this is a keyword search, not a classifier, and it should be possible
  to see exactly why any given paper was kept.

  Ambiguous language names are deliberately absent. Ethiopia has languages
  called Male, Chara, Bench, Dime, Zay and Opo, and searching for those returns
  papers about everything except them.

CONSENT

  This writes two files, and the difference between them matters.

    _data/generated/elsewhere.yml   published. Bibliographic facts: papers,
                                    venues, years, author names as printed.
    _data/invite_list.md            NOT published, git-ignored. The ranked list
                                    of people a maintainer might invite.

  The site's rule is that being findable is not consent to being listed as part
  of this community. A bibliography is a citation and needs no permission; a
  directory entry is a claim about a person and does. So the public page cites
  the work, and the invitation goes through the join form, where the person
  fills it in themselves.

    python3 scripts/sweep_literature.py
    python3 scripts/sweep_literature.py --check      # report, write nothing
    python3 scripts/sweep_literature.py --no-s2      # OpenAlex only, faster
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import socket
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.common import ROOT, info, step, warn  # noqa: E402

MEMBERS = ROOT / "_members"
GENERATED = ROOT / "_data" / "generated"
OUT = GENERATED / "elsewhere.yml"
INVITES = ROOT / "_data" / "invite_list.md"

OPENALEX = "https://api.openalex.org"
S2 = "https://api.semanticscholar.org/graph/v1"
CONTACT = "afriannotate@gmail.com"          # OpenAlex asks for this, politely
UA = "EthioNLP-site/1.0 (+https://ethionlp.github.io)"

# Language and country terms. Only names distinctive enough to search on: a
# term here that is also an ordinary English word floods the results and the
# NLP gate cannot rescue it.
SUBJECT_TERMS = [
    "Amharic", "Tigrinya", "Tigrigna", "Afaan Oromo", "Oromo language",
    "Wolaytta", "Wolaita", "Sidama", "Sidamo", "Afar language", "Somali language",
    "Ge'ez", "Geez language", "Hadiyya", "Kambaata", "Gurage", "Silt'e",
    "Awngi", "Gumuz", "Anuak", "Nuer language", "Kafa language", "Bench Maji",
    "Harari language", "Argobba", "Konso language", "Gedeo", "Ethiopic script",
    "Ethiopian languages", "Ethiopian language", "Ethiopic",
]

# NLP terms. A work must match one of these as well, in title or abstract.
#
# Every term here has to be unambiguous on its own, because one match is enough
# to keep a paper. That rules out several words that look like safe bets:
#
#   corpus, annotation   anatomy has a corpus callosum and genomics annotates
#                        genomes, and both are common in the public-health
#                        literature that a search for "Gedeo" or "Gumuz"
#                        returns, those being administrative zones as well as
#                        languages
#   transformer          electrical engineering had it first
#   dataset, benchmark   true of most quantitative papers in any field
#   multilingual         also sociolinguistics and education policy
#
# The compounds are listed instead: "parallel corpus" and "annotated corpus"
# earn their place where "corpus" does not. This is precision-first and it
# certainly misses some real work. A missed paper is recoverable by adding a
# term here; a page full of hepatitis studies is not.
#
# A trailing * means "stem": match the start of a word, so "tokeniz*" catches
# tokenizing and tokenization. Without it the term must stand as a whole word,
# which is what makes the acronyms safe to include at all.
NLP_TERMS = [
    "natural language processing", "computational linguistics", "nlp",
    "language model", "language modelling", "language modeling", "llm", "llms",
    "machine translation", "speech recognition", "speech corpus", "asr",
    "text-to-speech", "text to speech", "speech synthesis", "tts",
    "part-of-speech", "part of speech", "pos tagging", "postagging",
    "named entity", "sentiment analy*", "sentiment classif*", "hate speech",
    "offensive language", "abusive language", "text classification",
    "document classification", "information retrieval", "question answering",
    "summariz*", "summaris*", "morphological analy*", "morphological segment*",
    "morphological synthes*", "lemmatiz*", "lemmatis*", "tokeniz*", "tokenis*",
    "word embedding*", "sentence embedding*", "transliterat*",
    "optical character recognition", "ocr", "handwritten text recognition",
    "handwriting recognition", "character recognition", "spell check*",
    "spelling correction", "grammar checker", "grammatical error correction",
    "parallel corpus", "parallel corpora", "annotated corpus", "annotated corpora",
    "text corpus", "corpus development", "corpus construction", "treebank",
    "dependency pars*", "syntactic pars*", "cross-lingual", "crosslingual",
    "language identification", "topic model*", "word sense disambiguation",
    "information extraction", "relation extraction", "coreference",
    "stemming algorithm", "stemmer", "low-resource language*",
    "under-resourced language*", "sign language recognition",
    "neural machine translation", "statistical machine translation",
    "text summar*", "opinion mining", "fake news detection", "language technology",
]


def term_pattern(term: str) -> str:
    """A term as a whole word, or as a word-start when it ends in `*`.

    The guards are what stop `ocr` matching inside "democracy" and `bert`
    inside "Albert". Unguarded acronyms match inside ordinary words, which
    admits unrelated research wherever a language name is also a place name.
    """
    stem = term.endswith("*")
    body = re.escape(term[:-1] if stem else term)
    tail = "" if stem else r"(?![a-z])"
    return r"(?<![a-z])" + body + tail


SUBJECT_RE = re.compile("|".join(term_pattern(t.lower()) for t in SUBJECT_TERMS))
NLP_RE = re.compile("|".join(term_pattern(t.lower()) for t in NLP_TERMS))

# Fields whose papers are never about language technology, whatever words their
# abstracts happen to contain. OpenAlex assigns every work a topic and a field,
# and this is a far blunter and more reliable instrument than the keyword gate:
# "Gedeo" and "Gumuz" are administrative zones as well as languages, so those
# searches return hundreds of public-health papers, and no amount of keyword
# tuning distinguishes them as cleanly as the field label does.
#
# A denylist rather than an allowlist, so that a work OpenAlex has not
# classified is kept and judged on its keywords instead of silently dropped.
DENY_FIELDS = {
    "Medicine", "Nursing", "Health Professions", "Dentistry", "Veterinary",
    "Immunology and Microbiology", "Biochemistry, Genetics and Molecular Biology",
    "Agricultural and Biological Sciences", "Environmental Science",
    "Earth and Planetary Sciences", "Chemistry", "Chemical Engineering",
    "Materials Science", "Physics and Astronomy", "Energy", "Neuroscience",
    "Pharmacology, Toxicology and Pharmaceutics",
}

# Venue hints, matching the vocabulary sync_publications.py already uses so the
# type badge means the same thing on both publication pages.
PREPRINT_HINTS = ("arxiv", "corr", "preprint", "openreview", "biorxiv", "ssrn")
WORKSHOP_HINTS = ("workshop", "semeval", "winlp", "africanlp", "rail", "shared task", "wanlp")
CONFERENCE_HINTS = ("conference", "proceedings", "symposium", "acl", "lrec",
                    "coling", "emnlp", "naacl", "interspeech", "icassp")

# urlopen's `timeout` bounds each socket operation, not the request as a whole,
# so this is a backstop rather than a guarantee. The thing that actually stalls
# a run is the rate limiter, handled in get_json.
socket.setdefaulttimeout(60)

PER_PAGE = 200
MAX_PAGES = 4          # per term; 800 works each is far past the tail
TERM_BUDGET = 180      # seconds; abandon a term rather than wait on it
MAX_RETRY_WAIT = 90    # never sleep longer than this on a Retry-After header


class QuotaExhausted(RuntimeError):
    """The API's daily allowance is gone; waiting it out is not an option."""
PAGE_PAUSE = 1.0       # OpenAlex throttles an address that pages hard


# ── plumbing ─────────────────────────────────────────────────────────────────

def get_json(url: str, tries: int = 5) -> dict | None:
    """GET with a backoff long enough to actually clear a throttle.

    OpenAlex will throttle an address that pages hard, and it stays throttled
    for longer than a two-second retry covers, so a whole run can come back
    empty while looking like it worked. So the waits grow to a minute and Retry-After
    is honoured when the server sends one.
    """
    for attempt in range(tries):
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as fh:
                return json.loads(fh.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            # A 429 from OpenAlex is not always a passing throttle. The free
            # tier allows 1000 credits a day and a search costs 10, so about a
            # hundred requests; when they are gone the answer is 429 with
            # Retry-After set to whatever is left of the day. Sleeping for that
            # is not patience: a wait that long is indistinguishable from a
            # hung process. So the wait is capped, and a Retry-After longer than
            # the cap means the quota is spent and the run should stop and say
            # so rather than sleep through the reset.
            if exc.code == 429:
                hinted = (exc.headers.get("Retry-After") or "") if exc.headers else ""
                try:
                    wait = float(hinted)
                except ValueError:
                    wait = 0.0
                if wait > MAX_RETRY_WAIT:
                    remaining = (exc.headers.get("x-ratelimit-remaining") or "?"
                                 if exc.headers else "?")
                    raise QuotaExhausted(
                        f"OpenAlex daily quota is spent (remaining={remaining}); "
                        f"it resets in about {wait / 3600:.1f} hours. "
                        "Nothing was written. Run this again after the reset."
                    )
            if exc.code in (429, 500, 502, 503) and attempt < tries - 1:
                time.sleep([5, 15, 30, 60][min(attempt, 3)])
                continue
            warn(f"{exc.code} {url.split('?')[0]}")
            return None
        except Exception as exc:                       # noqa: BLE001
            if attempt < tries - 1:
                time.sleep(1 + attempt)
                continue
            warn(f"{type(exc).__name__} {url.split('?')[0]}")
            return None
    return None


def norm_name(s: str) -> str:
    """Fold a name to something two spellings of it can agree on."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z ]", " ", s.lower())
    return " ".join(s.split())


def name_keys(name: str) -> set[str]:
    """Keys a name can be matched on, to survive middle names being dropped.

    Ethiopian names are given name + father's name, and papers vary in whether
    the grandfather's name is printed. "Seid Muhie Yimam" and "Seid Yimam" are
    one person, so both the full fold and first+last are indexed.
    """
    n = norm_name(name)
    if not n:
        return set()
    parts = n.split()
    keys = {n}
    if len(parts) > 2:
        keys.add(f"{parts[0]} {parts[-1]}")
    # Indexes print both "Hellina Hailu Nigatu" and "Nigatu, Hellina Hailu".
    # The comma is stripped by norm_name, so the two forms differ only in word
    # order; a sorted-token key makes them agree. Without it, members came back
    # through this sweep and were published on /publications/elsewhere/ under
    # the heading "researchers who are not members".
    keys.add(" ".join(sorted(parts)))
    if len(parts) > 2:
        keys.add(" ".join(sorted((parts[0], parts[-1]))))
    return keys


def front_matter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="ignore")
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return {}
    try:
        return yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return {}


def load_members() -> tuple[set[str], set[str], set[str]]:
    """Every name key, ORCID and OpenAlex id belonging to a current member."""
    names, orcids, oa_ids = set(), set(), set()
    for path in sorted(MEMBERS.glob("*.md")):
        fm = front_matter(path)
        for field in ("name", "title"):
            names |= name_keys(str(fm.get(field) or ""))
        for alias in fm.get("aliases") or []:
            names |= name_keys(str(alias))
        orcid = str(fm.get("orcid") or "").strip().rstrip("/").split("/")[-1]
        if orcid:
            orcids.add(orcid.upper())
        oa = str(fm.get("openalex") or "").strip().rstrip("/").split("/")[-1]
        if oa:
            oa_ids.add(oa.upper())
    return names, orcids, oa_ids


# ── sources ──────────────────────────────────────────────────────────────────

def openalex_works(term: str) -> list[dict]:
    """Works whose title or abstract mentions `term`, newest first."""
    out, cursor = [], "*"
    deadline = time.monotonic() + TERM_BUDGET
    for _ in range(MAX_PAGES):
        if time.monotonic() > deadline:
            warn(f"{term}: gave up after {TERM_BUDGET}s, keeping {len(out)} so far")
            break
        params = urllib.parse.urlencode({
            "filter": f'title_and_abstract.search:"{term}"',
            "per-page": PER_PAGE,
            "cursor": cursor,
            "mailto": CONTACT,
        })
        doc = get_json(f"{OPENALEX}/works?{params}")
        if not doc:
            break
        results = doc.get("results") or []
        out += results
        cursor = (doc.get("meta") or {}).get("next_cursor")
        if not cursor or len(results) < PER_PAGE:
            break
        time.sleep(PAGE_PAUSE)
    return out


def field_of(work: dict) -> str | None:
    topic = work.get("primary_topic") or {}
    return ((topic.get("field") or {}).get("display_name")) or None


def inverted_to_text(index: dict | None) -> str:
    """OpenAlex ships abstracts as a word -> positions map, for licence reasons."""
    if not index:
        return ""
    words = [(pos, word) for word, spots in index.items() for pos in spots]
    words.sort()
    return " ".join(w for _, w in words[:400])


def from_openalex(term: str) -> list[dict]:
    kept = []
    for w in openalex_works(term):
        title = (w.get("title") or "").strip()
        if not title:
            continue
        field = field_of(w)
        if field in DENY_FIELDS:
            continue
        abstract = inverted_to_text(w.get("abstract_inverted_index"))
        hay = f"{title} {abstract}".lower()
        if not (SUBJECT_RE.search(hay) and NLP_RE.search(hay)):
            continue
        loc = (w.get("primary_location") or {}) or {}
        source = (loc.get("source") or {}) or {}
        authors = []
        for a in w.get("authorships") or []:
            au = a.get("author") or {}
            insts = [i.get("display_name") for i in (a.get("institutions") or []) if i.get("display_name")]
            authors.append({
                "name": (au.get("display_name") or "").strip(),
                "orcid": (au.get("orcid") or "").rstrip("/").split("/")[-1].upper() or None,
                "openalex": (au.get("id") or "").rstrip("/").split("/")[-1].upper() or None,
                "affiliation": insts[0] if insts else None,
                "countries": a.get("countries") or [],
            })
        kept.append({
            "title": title,
            "year": w.get("publication_year"),
            "venue": source.get("display_name"),
            "doi": (w.get("doi") or "").replace("https://doi.org/", "") or None,
            "url": loc.get("landing_page_url") or w.get("doi"),
            "open_access": bool(((w.get("open_access") or {}).get("is_oa"))),
            "citations": w.get("cited_by_count") or 0,
            "field": field,
            "authors": authors,
            "source": "openalex",
        })
    return kept


def from_s2(term: str) -> list[dict]:
    """Semantic Scholar, as a cross-check. Refusal here is not a failure."""
    fields = ("title,year,venue,externalIds,openAccessPdf,citationCount,"
              "fieldsOfStudy,authors.name,authors.authorId")
    # Semantic Scholar's vocabulary is its own, so the denylist is spelled out
    # again here rather than shared with the OpenAlex one.
    deny = {"Medicine", "Biology", "Chemistry", "Physics", "Materials Science",
            "Environmental Science", "Geology", "Agricultural and Food Sciences",
            "Psychology", "Economics", "Business", "Geography"}
    kept, offset = [], 0
    while offset < 300:
        params = urllib.parse.urlencode({
            "query": term, "fields": fields, "limit": 100, "offset": offset,
        })
        doc = get_json(f"{S2}/paper/search?{params}", tries=2)
        if not doc or not doc.get("data"):
            break
        for p in doc["data"]:
            title = (p.get("title") or "").strip()
            hay = title.lower()
            if not (SUBJECT_RE.search(hay) and NLP_RE.search(hay)):
                continue          # no abstract requested, so the title must carry it
            fos = set(p.get("fieldsOfStudy") or [])
            if fos and fos <= deny:
                continue          # every field it has is one we exclude
            ext = p.get("externalIds") or {}
            kept.append({
                "title": title,
                "year": p.get("year"),
                "venue": p.get("venue") or None,
                "doi": ext.get("DOI"),
                "url": (f"https://aclanthology.org/{ext['ACL']}/" if ext.get("ACL")
                        else f"https://doi.org/{ext['DOI']}" if ext.get("DOI") else None),
                "open_access": bool(p.get("openAccessPdf")),
                "citations": p.get("citationCount") or 0,
                "authors": [{"name": (a.get("name") or "").strip(), "orcid": None,
                             "openalex": None, "affiliation": None, "countries": []}
                            for a in (p.get("authors") or [])],
                "source": "semantic_scholar",
            })
        offset += 100
        time.sleep(1.2)                       # unauthenticated: be a good guest
    return kept


# ── assembly ─────────────────────────────────────────────────────────────────

def title_key(title: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (title or "").lower())[:90]


def absorb(cur: dict, rec: dict) -> None:
    """Fold `rec` into `cur`, keeping whichever of the two knows more."""
    seen = set(cur.get("sources") or []) | set(rec.get("sources") or [])
    if rec.get("source"):
        seen.add(rec["source"])
    cur["sources"] = sorted(seen - {""})
    if len(rec.get("authors") or []) > len(cur.get("authors") or []):
        cur["authors"] = rec["authors"]
    for field in ("venue", "doi", "url", "year", "field"):
        if not cur.get(field) and rec.get(field):
            cur[field] = rec[field]
    cur["citations"] = max(cur.get("citations") or 0, rec.get("citations") or 0)
    cur["open_access"] = cur.get("open_access") or rec.get("open_access")


def merge(records: list[dict]) -> list[dict]:
    """One entry per work, preferring the record that knows the most.

    Two passes, and the second one matters. Keying on "DOI, or title if there
    is no DOI" leaves the same paper duplicated whenever two records carry
    different DOIs: an arXiv preprint and the published version, or a
    conference paper indexed twice. A single paper can survive as several
    entries that way, and because author counts rank the people on the page,
    each duplicate inflates its authors' totals. So DOIs merge first, then
    titles merge across whatever DOI groups remain.
    """
    by_key: dict[str, dict] = {}
    for rec in records:
        key = (rec.get("doi") or "").lower() or title_key(rec["title"])
        if not key:
            continue
        cur = by_key.get(key)
        if cur is None:
            # `source` on a freshly fetched record, `sources` on one being
            # re-merged from the stored file. Tolerating both means the merge
            # can be re-applied to existing data without a second round of
            # fetching, which is what a rate limit makes valuable.
            first = rec.pop("source", None)
            rec["sources"] = sorted(set(rec.get("sources") or []) | ({first} if first else set()))
            by_key[key] = rec
            continue
        absorb(cur, rec)

    # Second pass: collapse anything left that is the same title under two
    # different DOIs. Keep the record with the DOI where only one has one, so
    # the surviving entry still links somewhere.
    by_title: dict[str, dict] = {}
    for rec in by_key.values():
        key = title_key(rec["title"])
        if not key:
            continue
        cur = by_title.get(key)
        if cur is None:
            by_title[key] = rec
            continue
        if rec.get("doi") and not cur.get("doi"):
            rec_sources = cur.get("sources") or []
            absorb(rec, cur)
            rec["sources"] = sorted(set((rec.get("sources") or []) + rec_sources) - {""})
            by_title[key] = rec
        else:
            absorb(cur, rec)
    return list(by_title.values())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="report, write nothing")
    parser.add_argument("--no-s2", action="store_true", help="skip Semantic Scholar")
    args = parser.parse_args()

    member_names, member_orcids, member_oa = load_members()
    info(f"{len(member_names)} name keys, {len(member_orcids)} ORCIDs, "
         f"{len(member_oa)} OpenAlex ids from {len(list(MEMBERS.glob('*.md')))} members")

    step(f"Searching {len(SUBJECT_TERMS)} subject terms")
    raw: list[dict] = []
    for term in SUBJECT_TERMS:
        try:
            found = from_openalex(term)
        except QuotaExhausted as exc:
            warn(str(exc))
            return 2
        if not args.no_s2:
            found += from_s2(term)
        info(f"  {term:24} {len(found):4} kept")
        raw += found

    works = merge(raw)
    works.sort(key=lambda w: (-(w.get("year") or 0), -(w.get("citations") or 0)))
    step(f"{len(works)} distinct works after merging {len(raw)} records")

    # Who wrote them, and which of those are already here.
    people: dict[str, dict] = {}
    member_works = 0
    for w in works:
        names_on_paper = [a["name"] for a in w["authors"] if a["name"]]
        w["has_member"] = False
        for a in w["authors"]:
            if not a["name"]:
                continue
            keys = name_keys(a["name"])
            is_member = (
                bool(keys & member_names)
                or (a.get("orcid") and a["orcid"] in member_orcids)
                or (a.get("openalex") and a["openalex"] in member_oa)
            )
            if is_member:
                w["has_member"] = True
                continue
            key = sorted(keys)[0] if keys else None
            if not key:
                continue
            rec = people.setdefault(key, {
                "name": a["name"], "orcid": a.get("orcid"),
                "openalex": a.get("openalex"), "affiliation": a.get("affiliation"),
                "countries": [], "works": 0, "citations": 0, "years": [],
                "coauthored_with_member": False,
            })
            rec["works"] += 1
            rec["citations"] += w.get("citations") or 0
            if w.get("year"):
                rec["years"].append(w["year"])
            for c in a.get("countries") or []:
                if c not in rec["countries"]:
                    rec["countries"].append(c)
            if not rec["affiliation"] and a.get("affiliation"):
                rec["affiliation"] = a["affiliation"]
            if not rec["orcid"] and a.get("orcid"):
                rec["orcid"] = a["orcid"]
            rec["_names"] = rec.get("_names", set()) | {a["name"]}
        if w["has_member"]:
            member_works += 1
            for a in w["authors"]:
                keys = name_keys(a["name"])
                key = sorted(keys)[0] if keys else None
                if key in people:
                    people[key]["coauthored_with_member"] = True
        # `type` and `author_line` are what _includes/pub-item.html reads, so
        # these records render through the same component as members' papers
        # rather than needing a second, drifting copy of that markup.
        w["author_names"] = names_on_paper
        w["author_line"] = ", ".join(names_on_paper)
        venue = (w.get("venue") or "").lower()
        w["type"] = (
            "preprint" if any(h in venue for h in PREPRINT_HINTS)
            else "workshop" if any(h in venue for h in WORKSHOP_HINTS)
            else "conference" if any(h in venue for h in CONFERENCE_HINTS)
            else "journal" if venue
            else "paper"
        )

    for rec in people.values():
        # The fullest spelling seen, since papers vary in whether they print
        # the third name and the longer form is the more identifying one.
        rec["name"] = sorted(rec.pop("_names", {rec["name"]}), key=len)[-1]
        rec["first_year"] = min(rec["years"]) if rec["years"] else None
        rec["last_year"] = max(rec["years"]) if rec["years"] else None
        rec.pop("years", None)

    ranked = sorted(people.values(),
                    key=lambda r: (-r["works"], -r["citations"], r["name"]))

    step("Result")
    info(f"{len(works)} works, {member_works} with a member on them")
    info(f"{len(ranked)} distinct authors who are not members")
    info(f"{sum(1 for r in ranked if r['works'] >= 3)} of them with 3 or more works")
    info(f"{sum(1 for r in ranked if r['coauthored_with_member'])} have co-authored with a member")
    for r in ranked[:12]:
        aff = r["affiliation"] or "affiliation unknown"
        info(f"  {r['works']:3}  {r['name'][:34]:34} {aff[:40]}")

    if args.check:
        info("--check: nothing written")
        return 0

    # A throttled run looks exactly like a successful one that found nothing:
    # every request fails, every term reports zero, and an empty file would
    # replace a complete one. So refuse to publish a result that has collapsed
    # against what is already on disk.
    if OUT.exists():
        try:
            previous = (yaml.safe_load(OUT.read_text(encoding="utf-8")) or {})
            had = ((previous.get("counts") or {}).get("works")) or 0
        except yaml.YAMLError:
            had = 0
        if had and len(works) < had / 2:
            warn(f"found {len(works)} works but the last run found {had}; "
                 "refusing to overwrite. This is usually rate limiting; "
                 "wait a few minutes and run it again.")
            return 1
    if not works:
        warn("no works found at all; writing nothing")
        return 1

    ethiopian = [w for w in works if not w["has_member"]]
    doc = {
        "generated": True,
        "method": (
            "Searched OpenAlex and Semantic Scholar by subject, not by author. A "
            "work is kept when its title or abstract names an Ethiopian language "
            "and an NLP topic. ACL Anthology, IEEE and AAAI papers arrive through "
            "the DOIs those publishers deposit; anything not deposited is not here."
        ),
        "terms": SUBJECT_TERMS,
        "counts": {
            "works": len(works),
            "works_without_member": len(ethiopian),
            "authors_not_members": len(ranked),
        },
        # Only the papers with nobody from the directory on them. The page is
        # headed "papers with no EthioNLP member among the authors", and
        # publishing the whole set under that heading would have contradicted
        # the count printed directly above it. The ones with a member on them
        # are already on /publications/, so nothing is lost by leaving them out.
        "works": ethiopian,
        "authors": ranked,
    }
    GENERATED.mkdir(parents=True, exist_ok=True)
    OUT.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=100),
                   encoding="utf-8")
    info(f"wrote {OUT.relative_to(ROOT)}")

    # The invite list is a working file, not a page. See CONSENT above.
    lines = [
        "# Possible people to invite",
        "",
        "Generated by scripts/sweep_literature.py. **Not published**: this file",
        "is git-ignored, because appearing in a bibliography is not consent to",
        "being listed in a community directory. Use it to decide who to write to;",
        "send them the join form and let them fill it in themselves:",
        "",
        "  https://github.com/EthioNLP/ethionlp.github.io/issues/new?template=join-community.yml",
        "",
        "Ordered by number of matching works. `co-authored` means they have",
        "already published with somebody in the directory, which usually makes",
        "them the easiest to reach.",
        "",
        "| Works | Name | Affiliation | Active | Co-authored | ORCID |",
        "| ----: | ---- | ----------- | ------ | ----------- | ----- |",
    ]
    for r in ranked:
        if r["works"] < 2:
            continue
        span = (f"{r['first_year']}–{r['last_year']}"
                if r["first_year"] and r["first_year"] != r["last_year"]
                else str(r["last_year"] or ""))
        lines.append(
            f"| {r['works']} | {r['name']} | {r['affiliation'] or ''} | {span} | "
            f"{'yes' if r['coauthored_with_member'] else ''} | {r['orcid'] or ''} |"
        )
    INVITES.write_text("\n".join(lines) + "\n", encoding="utf-8")
    info(f"wrote {INVITES.relative_to(ROOT)} (git-ignored)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
