#!/usr/bin/env python3
"""Check that every paper in the sweep is actually language-technology research.

sweep_literature.py keeps a paper when its title or abstract names an Ethiopian
language and a topic word. That is a test of vocabulary, not of subject. A
paper can satisfy it without being NLP research at all: several Ethiopian
languages share a name with an administrative zone, and a health or agriculture
study from that zone can use a word like "classification" in its ordinary
sense.

So this asks a second, independent question of every kept paper: what is this
paper about? OpenAlex assigns each work a topic, a subfield, a field and a set
of concepts, all derived from the full record rather than from the words the
sweep happened to match. Those are fetched here in batches of fifty by DOI and
weighed against the title and abstract.

A paper is kept when at least one of these holds:

  topic       its OpenAlex topic, subfield or concepts name language
              technology, artificial intelligence, machine learning or
              information science
  phrase      its title or abstract contains a phrase that only appears in
              language-technology work, such as "machine translation" or
              "part-of-speech tagging"

and dropped otherwise. Every decision is recorded on the record as `relevance`
with the reason, so a maintainer can see why any given paper stayed or went and
correct the rule rather than the paper.

Papers with no DOI cannot be looked up in batch and are judged on the title,
venue and the field already stored; they are marked `unverified` when they pass
on that weaker evidence alone.

    python3 scripts/verify_topics.py            # check and rewrite
    python3 scripts/verify_topics.py --check    # report, write nothing
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.common import ROOT, info, step, warn  # noqa: E402

DATA = ROOT / "_data" / "generated" / "elsewhere.yml"
OPENALEX = "https://api.openalex.org"
CONTACT = "afriannotate@gmail.com"
UA = "EthioNLP-site/1.0 (+https://ethionlp.github.io)"
BATCH = 50          # OpenAlex accepts up to 50 values in one OR filter

# The free tier allows about a hundred requests a day, and tuning the rules
# below takes more runs than that. Responses are cached so only the first run
# spends quota; delete the file to force a refresh.
CACHE = ROOT / "scripts" / ".cache" / "openalex_topics.json"

# Topic, subfield and concept names that mean the work is language technology,
# AI, machine learning or data science. Matched case-insensitively as
# substrings, so "Natural Language Processing" also catches OpenAlex's
# "Topic Modeling and Natural Language Processing".
TOPIC_MARKERS = (
    "natural language processing", "computational linguistics", "linguistics",
    "speech recognition", "speech processing", "speech synthesis",
    "machine translation", "artificial intelligence", "machine learning",
    "deep learning", "neural network", "information retrieval",
    "text mining", "text classification", "sentiment analysis",
    "information systems", "computer vision", "pattern recognition",
    "optical character recognition", "document analysis", "data science",
    "data mining", "human-computer interaction", "language models",
    "semantic web", "knowledge representation", "topic modeling",
    "topic modelling", "computer science", "software", "algorithms",
)

# Fields that are never language technology, whatever a topic string says.
FIELD_DENY = {
    "Medicine", "Nursing", "Health Professions", "Dentistry", "Veterinary",
    "Immunology and Microbiology", "Biochemistry, Genetics and Molecular Biology",
    "Agricultural and Biological Sciences", "Environmental Science",
    "Earth and Planetary Sciences", "Chemistry", "Chemical Engineering",
    "Materials Science", "Physics and Astronomy", "Energy", "Neuroscience",
    "Pharmacology, Toxicology and Pharmaceutics", "Economics, Econometrics and Finance",
    "Business, Management and Accounting", "Psychology",
}

# Phrases that appear only in language-technology work. Deliberately narrower
# than the sweep's keyword list: this is the evidence that can carry a paper on
# its own when the topic labels are missing or unhelpful.
STRONG_PHRASES = (
    "natural language processing", "computational linguistics",
    "machine translation", "speech recognition", "speech synthesis",
    "text-to-speech", "part-of-speech", "part of speech", "pos tagging",
    "named entity", "sentiment analysis", "sentiment classification",
    "hate speech detection", "text classification", "document classification",
    "information retrieval", "question answering", "text summarization",
    "text summarisation", "morphological analysis", "morphological segmentation",
    "lemmatization", "lemmatisation", "tokenization", "tokenisation",
    "word embedding", "sentence embedding", "language model",
    "optical character recognition", "handwriting recognition",
    "character recognition", "spelling correction", "grammar checker",
    "parallel corpus", "parallel corpora", "annotated corpus", "treebank",
    "dependency parsing", "syntactic parsing", "cross-lingual",
    "language identification", "topic modeling", "topic modelling",
    "word sense disambiguation", "information extraction", "speech corpus",
    "stemming algorithm", "stemmer", "transliteration", "corpus linguistics",
    "neural machine translation", "statistical machine translation",
    "low-resource language", "under-resourced language", "opinion mining",
    "automatic speech", "language technology", "corpus development",
    "spelling error", "spelling detection", "spell checker", "semantic role",
    "semantic role labeling", "semantic role labelling", "word segmentation",
    "text normalization", "text normalisation", "speech dataset", "text corpus",
    "language resource", "linguistic annotation", "keyword spotting",
    "abstractive", "extractive summar", "code-switch", "codeswitch",
    "phrase structure grammar", "head-driven phrase",
)

# Acronyms and short forms, which need word boundaries: "ocr" must not match
# inside "microcredit", and "asr" must not match inside "phrase".
STRONG_ACRONYMS = ("ocr", "asr", "nlp", "tts", "mt", "ner", "llm", "srl", "smt",
                   "nmt", "pos", "hmm", "crf")

# Fields where a paper that already mentions an Ethiopian language and a topic
# word is language technology or computing research about that language. This
# carries the papers whose topic labels are missing, which is most of the ones
# with no DOI to look up.
COMPUTING_FIELDS = {"Computer Science", "Engineering", "Mathematics", "Decision Sciences"}

# A field label alone is the weakest evidence used here, and OpenAlex sometimes
# files a paper under a field it plainly does not belong to. So a paper carried
# by its field must also show a language-technology word in its own title: the
# sweep may have matched only the abstract, which is how an agronomy paper on
# Ethiopian Jatropha arrived under a Computer Science label.
TITLE_HINT_RE = re.compile(
    r"(?<![a-z])("
    r"languag|linguistic|corpus|corpora|text|speech|voice|translat|recogni"
    r"|parser|pars(e|ing)|tagg|token|morpholog|semantic|syntax|syntactic"
    r"|summar|sentiment|classif|detect|identif|retriev|extract|annotat"
    r"|dataset|data set|document|script|font|charact|word|sentence|dialect"
    r"|question answer|chatbot|search|transcri|phonolog|orthograph|lexic"
    r"|spell|grammar|treebank|stemm|embedding"
    # The literature on these languages is not only in English. TAL is the
    # French term for NLP and appears in the title rather than the abstract.
    r"|langue|traitement automatique|sprach|informatis|lingua"
    r")", re.I)

# Acronyms need a closing boundary as well, so "qa" does not match "Qatar"
# and "mt" does not match "mtDNA".
TITLE_ACRONYM_RE = re.compile(
    r"(?<![a-z])(nlp|ocr|asr|mt|ner|llm|qa|tal|tts|smt|nmt|srl|hlt)(?![a-z])", re.I)

PHRASE_RE = re.compile(
    "|".join([re.escape(p) for p in STRONG_PHRASES]
             + [r"(?<![a-z])" + re.escape(a) + r"(?![a-z])" for a in STRONG_ACRONYMS])
)
TOPIC_RE = re.compile("|".join(re.escape(t) for t in TOPIC_MARKERS))


def get_json(url: str, tries: int = 3) -> dict | None:
    for attempt in range(tries):
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as fh:
                return json.loads(fh.read().decode("utf-8"))
        except Exception as exc:                            # noqa: BLE001
            if attempt < tries - 1:
                time.sleep(3 * (attempt + 1))
                continue
            warn(f"{type(exc).__name__} on {url.split('?')[0]}")
            return None
    return None


def inverted_to_text(index: dict | None) -> str:
    if not index:
        return ""
    words = [(pos, w) for w, spots in index.items() for pos in spots]
    words.sort()
    return " ".join(w for _, w in words[:400])


def fetch_by_doi(dois: list[str]) -> dict[str, dict]:
    """OpenAlex records for a list of DOIs, keyed by lowercased DOI."""
    out: dict[str, dict] = {}
    if CACHE.exists():
        try:
            out = json.loads(CACHE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            out = {}
    missing = [d for d in dois if d and d not in out]
    if not missing:
        info(f"  {len(out)} records from cache, nothing to fetch")
        return out
    info(f"  {len(out)} cached, fetching {len(missing)}")
    dois = missing
    for i in range(0, len(dois), BATCH):
        chunk = [d for d in dois[i:i + BATCH] if d]
        if not chunk:
            continue
        params = urllib.parse.urlencode({
            "filter": "doi:" + "|".join(chunk),
            "per-page": BATCH,
            "select": "doi,title,primary_topic,topics,concepts,abstract_inverted_index",
            "mailto": CONTACT,
        })
        doc = get_json(f"{OPENALEX}/works?{params}")
        if not doc:
            continue
        for rec in doc.get("results") or []:
            doi = (rec.get("doi") or "").replace("https://doi.org/", "").lower()
            if doi:
                out[doi] = rec
        info(f"  fetched {len(out)} in total")
        time.sleep(0.5)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(out), encoding="utf-8")
    return out


def topic_labels(rec: dict) -> tuple[list[str], str | None]:
    """Every topic-ish label on a record, plus its field."""
    labels: list[str] = []
    primary = rec.get("primary_topic") or {}
    field = ((primary.get("field") or {}).get("display_name")) or None
    for key in ("display_name",):
        if primary.get(key):
            labels.append(primary[key])
    for part in ("subfield", "field", "domain"):
        name = ((primary.get(part) or {}).get("display_name"))
        if name:
            labels.append(name)
    for t in (rec.get("topics") or [])[:3]:
        if t.get("display_name"):
            labels.append(t["display_name"])
        sub = ((t.get("subfield") or {}).get("display_name"))
        if sub:
            labels.append(sub)
    for c in (rec.get("concepts") or []):
        # Concepts carry a score; a weak association is not evidence.
        if (c.get("score") or 0) >= 0.3 and c.get("display_name"):
            labels.append(c["display_name"])
    return labels, field


def judge(work: dict, rec: dict | None) -> dict:
    """Decide whether a paper is language-technology research, and say why."""
    title = (work.get("title") or "").lower()
    abstract = inverted_to_text((rec or {}).get("abstract_inverted_index"))
    haystack = f"{title} {abstract}".lower()

    labels, field = ([], None)
    if rec:
        labels, field = topic_labels(rec)
    field = field or work.get("field")

    phrase = PHRASE_RE.search(haystack)
    label_hit = None
    for label in labels:
        if TOPIC_RE.search(label.lower()):
            label_hit = label
            break

    # A denied field can still be right when the paper itself is plainly about
    # language technology, so the phrase test can override it; a field alone
    # cannot rescue a paper with no other evidence.
    if field in FIELD_DENY and not phrase:
        return {"keep": False, "why": f"field is {field}, no language-technology phrase",
                "field": field, "verified": bool(rec)}
    if label_hit:
        return {"keep": True, "why": f"topic: {label_hit}", "field": field, "verified": bool(rec)}
    if phrase:
        return {"keep": True, "why": f"phrase: {phrase.group(0)}", "field": field,
                "verified": bool(rec)}
    if field in COMPUTING_FIELDS:
        title_raw = work.get("title") or ""
        if TITLE_HINT_RE.search(title_raw) or TITLE_ACRONYM_RE.search(title_raw):
            return {"keep": True, "why": f"field: {field}", "field": field,
                    "verified": bool(rec)}
        return {"keep": False,
                "why": f"field is {field} but the title shows no language-technology subject",
                "field": field, "verified": bool(rec)}
    if not field:
        title_raw = work.get("title") or ""
        if TITLE_HINT_RE.search(title_raw) or TITLE_ACRONYM_RE.search(title_raw):
            return {"keep": True, "why": "title only, no field recorded",
                    "field": None, "verified": False}
    return {"keep": False,
            "why": ("no language-technology topic or phrase" if rec else
                    "no DOI to check, and neither the title nor the recorded "
                    "field indicates language technology"),
            "field": field, "verified": bool(rec)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report, write nothing")
    args = ap.parse_args()

    doc = yaml.safe_load(DATA.read_text(encoding="utf-8")) or {}
    works = doc.get("works") or []
    if not works:
        warn("no works to verify")
        return 1

    dois = [(w.get("doi") or "").lower() for w in works if w.get("doi")]
    step(f"Fetching topics for {len(dois)} of {len(works)} works")
    records = fetch_by_doi(dois)
    info(f"{len(records)} records returned")

    step("Judging")
    kept, dropped = [], []
    reasons: collections.Counter = collections.Counter()
    for w in works:
        rec = records.get((w.get("doi") or "").lower())
        verdict = judge(w, rec)
        w["relevance"] = verdict
        (kept if verdict["keep"] else dropped).append(w)
        reasons[verdict["why"].split(":")[0]] += 1

    info(f"kept {len(kept)}, dropped {len(dropped)}")
    for why, n in reasons.most_common():
        info(f"  {why:52} {n}")

    info("")
    info("Sample of what is being dropped:")
    for w in dropped[:12]:
        info(f"  [{str(w['relevance'].get('field'))[:18]:18}] {w['title'][:66]}")

    if args.check:
        info("--check: nothing written")
        return 0

    # Author totals rank the people on the page, so they have to be counted
    # from the papers that survived this check rather than from the set the
    # sweep produced.
    people: dict[str, dict] = {}
    coauth = {n["name"]: n.get("coauthored_with_member")
              for n in (doc.get("authors") or [])}
    for w in kept:
        for a in w.get("authors") or []:
            name = (a.get("name") or "").strip()
            if not name:
                continue
            rec = people.setdefault(name, {
                "name": name, "orcid": a.get("orcid"), "openalex": a.get("openalex"),
                "affiliation": a.get("affiliation"), "countries": [],
                "works": 0, "citations": 0, "_years": [],
                "coauthored_with_member": bool(coauth.get(name)),
            })
            rec["works"] += 1
            rec["citations"] += w.get("citations") or 0
            if w.get("year"):
                rec["_years"].append(w["year"])
            if not rec["affiliation"] and a.get("affiliation"):
                rec["affiliation"] = a["affiliation"]
            if not rec["orcid"] and a.get("orcid"):
                rec["orcid"] = a["orcid"]
    for rec in people.values():
        years = rec.pop("_years")
        rec["first_year"] = min(years) if years else None
        rec["last_year"] = max(years) if years else None
    ranked = sorted(people.values(),
                    key=lambda r: (-r["works"], -r["citations"], r["name"]))
    info(f"authors recounted: {len(ranked)}, "
         f"{sum(1 for r in ranked if r['works'] >= 3)} with three or more")

    doc["works"] = kept
    doc["authors"] = ranked
    doc["counts"] = dict(doc.get("counts") or {})
    doc["counts"]["authors_not_members"] = len(ranked)
    doc["counts"]["works_without_member"] = len(kept)
    # Cumulative, not per-run: re-running on an already-filtered file drops
    # nothing, and a count that reset to zero would read as "nothing was ever
    # removed" on the page that reports it.
    previously = (doc.get("counts") or {}).get("dropped_off_topic") or 0
    doc["counts"]["dropped_off_topic"] = previously + len(dropped)
    doc["topic_check"] = (
        "Every paper was checked a second time against the topic, subfield and "
        "concepts OpenAlex assigns it, which are derived from the whole record "
        f"rather than from the words the search matched. {len(dropped)} papers "
        "that named a language and a topic word without being language-"
        "technology research were removed."
    )
    DATA.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=100),
                    encoding="utf-8")
    info(f"wrote {DATA.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
