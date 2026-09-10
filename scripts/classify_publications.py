#!/usr/bin/env python3
"""Assign each publication to one or more of the six research tracks.

The tracks on /research/ are how this community describes its own work, but
until now nothing connected them to the papers. A reader could see six tracks
and 256 papers and had no way to get from one to the other.

This closes that, by matching keywords against the title, venue and abstract.
Keyword rules rather than a model, for three reasons: the result has to be
inspectable, a maintainer has to be able to correct it by editing one line, and
a paper that matches nothing should stay unassigned rather than be forced into
the nearest bucket.

It writes `tracks: [...]` onto each record in the generated publications file,
so it must run after sync_publications.py. A paper matching nothing gets an
empty list and is grouped as "Not yet classified", which is honest and is also
the queue of things to add a keyword for.

    python3 scripts/classify_publications.py
    python3 scripts/classify_publications.py --check   # report, write nothing
"""

from __future__ import annotations

import argparse
import collections
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.common import ROOT, info, step, warn  # noqa: E402

PUBS = ROOT / "_data" / "generated" / "publications.yml"

# Matched against title + venue + abstract, lowercased, on word boundaries.
# Order does not matter; a paper can belong to several tracks, and most do.
#
# Keep these specific. "model" alone would swallow the entire corpus; "language
# model" earns its place. When a paper lands in the wrong track, the fix is to
# make a keyword narrower here rather than to special-case the paper.
RULES: dict[str, tuple[str, ...]] = {
    "data": (
        "corpus", "corpora", "dataset", "data set", "annotation", "annotated",
        "treebank", "parallel text", "parallel corpus", "crawl", "collection",
        "transcription", "transcribed", "lexicon", "wordlist", "resource creation",
    ),
    "models": (
        "language model", "llm", "pretrain", "pre-train", "fine-tun", "finetun",
        "transformer", "bert", "roberta", "gpt", "encoder", "decoder", "embedding",
        "tokeniz", "tokenis", "neural machine translation", "seq2seq", "adapter",
    ),
    "applications": (
        "machine translation", "speech recognition", "asr", "text-to-speech",
        "question answering", "information retrieval", "search engine",
        "sentiment", "hate speech", "abusive", "offensive", "toxic",
        "classification", "named entity", "summaris", "summariz", "chatbot",
        "spell check", "optical character", "ocr", "accessibility", "sign language",
        "emotion", "detoxif", "fake news", "misinformation", "disinformation",
        "polaris", "polariz", "recommend", "dialogue system", "speech synthesis",
    ),
    "evaluation": (
        "benchmark", "evaluation", "evaluat", "shared task", "semeval",
        "leaderboard", "error analysis", "metric", "human judgement",
        "human judgment", "contamination", "probing", "bias", "fairness",
        "robustness", "ablation",
    ),
    "capacity": (
        "curriculum", "teaching", "training workshop", "capacity building",
        "student", "education", "tutorial", "community building", "participatory",
    ),
    "linguistics": (
        "morpholog", "syntax", "syntactic", "phonolog", "orthograph",
        "dialect", "grammar", "linguistic analysis", "part-of-speech",
        "part of speech", "pos tagging", "segmentation", "documentation",
        "typolog", "historical reconstruction",
    ),
}


def haystack(rec: dict) -> str:
    parts = [rec.get("title") or "", rec.get("venue") or "", rec.get("abstract") or ""]
    return re.sub(r"\s+", " ", " ".join(parts)).lower()


def tracks_for(rec: dict) -> list[str]:
    text = haystack(rec)
    hits = []
    for track, words in RULES.items():
        for w in words:
            # Word-boundary at the start only: "annotat" should catch
            # "annotated" and "annotation", but "asr" must not match "phrase".
            if re.search(r"(?<![a-z])" + re.escape(w), text):
                hits.append(track)
                break
    return hits


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="report, write nothing")
    args = parser.parse_args()

    if not PUBS.exists():
        warn("publications.yml not found; run sync_publications.py first")
        return 1

    doc = yaml.safe_load(PUBS.read_text(encoding="utf-8")) or {}
    records = doc.get("publications") or []
    if not records:
        warn("no publications to classify")
        return 1

    step(f"Classifying {len(records)} publications")
    counts: collections.Counter = collections.Counter()
    unassigned = []
    for rec in records:
        hits = tracks_for(rec)
        rec["tracks"] = hits
        for h in hits:
            counts[h] += 1
        if not hits:
            unassigned.append(rec.get("title") or "(untitled)")

    for key in RULES:
        info(f"{key:14} {counts[key]:4}")
    info(f"{'unassigned':14} {len(unassigned):4}")

    # An abstract is what makes classification work; without one there is only
    # a title to go on, so say how many are in that position.
    no_abstract = sum(1 for r in records if not r.get("abstract"))
    info(f"{'no abstract':14} {no_abstract:4}  (title and venue only)")

    if args.check:
        for t in unassigned[:15]:
            info(f"  unassigned: {t[:72]}")
        info("--check: nothing written")
        return 0

    doc["publications"] = records
    PUBS.write_text(
        yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )
    info(f"wrote tracks into {PUBS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
