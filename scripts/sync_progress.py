#!/usr/bin/env python3
"""Sync the NLP-progress dashboard into _data/generated/progress.yml.

Counts, per year, how many NLP papers mention each language. The query is an
OpenAlex title-and-abstract search intersected with the "Natural language
processing" concept (C204321447), the intersection matters: an unfiltered
search for "Amharic" also returns clinical and sociolinguistic papers, which
would flatter the numbers badly.

The same query shape is used for Ethiopian and for comparison African languages,
so the two lines on the chart are measured identically. That is the only claim
the chart makes; it is not a count of "all Ethiopian NLP research".

Usage:  python3 scripts/sync_progress.py [--dry-run] [--from 2010] [--to 2025]
"""

from __future__ import annotations

import argparse
import sys
import urllib.parse
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.common import (  # noqa: E402
    CONTACT_EMAIL,
    get_json,
    info,
    load_curated,
    step,
    touch_meta,
    warn,
    write_generated,
)

OPENALEX = "https://api.openalex.org"
NLP_CONCEPT = "C204321447"  # OpenAlex: Natural language processing

TRACKS = [
    # key, display name, OpenAlex search term, which track it belongs to
    ("amharic",  "Amharic",     "amharic",  "ethiopia"),
    ("tigrinya", "Tigrinya",    "tigrinya", "ethiopia"),
    ("oromo",    "Afaan Oromo", "oromo",    "ethiopia"),
    ("somali",   "Somali",      "somali",   "ethiopia"),
    ("swahili",  "Swahili",     "swahili",  "africa"),
    ("yoruba",   "Yoruba",      "yoruba",   "africa"),
    ("hausa",    "Hausa",       "hausa",    "africa"),
    ("igbo",     "Igbo",        "igbo",     "africa"),
]


def counts_by_year(term: str) -> dict[int, int]:
    url = (
        f"{OPENALEX}/works"
        f"?filter=title_and_abstract.search:{urllib.parse.quote(term)},concepts.id:{NLP_CONCEPT}"
        f"&group_by=publication_year&mailto={CONTACT_EMAIL}"
    )
    page = get_json(url)
    if not page:
        warn(f"no data for {term!r}")
        return {}
    out = {}
    for group in page.get("group_by", []):
        try:
            out[int(group["key"])] = int(group["count"])
        except (KeyError, TypeError, ValueError):
            continue
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--from", dest="start", type=int, default=2010)
    # The running year is excluded by default. It is always incomplete, and
    # OpenAlex indexes recent work in bursts, so plotting it produces a spike
    # that reads as a discovery and is really a data-collection artefact.
    parser.add_argument("--to", dest="end", type=int, default=date.today().year - 1)
    args = parser.parse_args()

    years = list(range(args.start, args.end + 1))
    series = []

    step(f"OpenAlex, {args.start}–{args.end}, NLP concept only")
    for key, label, term, track in TRACKS:
        data = counts_by_year(term)
        points = [data.get(year, 0) for year in years]
        series.append({
            "key": key,
            "label": label,
            "track": track,
            "term": term,
            "points": points,
            "total": sum(points),
        })
        info(f"{label:<12} {sum(points):>5} papers  ({points[0]} → {points[-1]})")

    ethiopia = [
        sum(s["points"][i] for s in series if s["track"] == "ethiopia")
        for i in range(len(years))
    ]
    africa = [
        sum(s["points"][i] for s in series if s["track"] == "africa")
        for i in range(len(years))
    ]

    def growth(points: list[int]) -> float | None:
        """Ratio of the last three years to the first three, as a coarse trend."""
        if len(points) < 6:
            return None
        early = sum(points[:3])
        late = sum(points[-3:])
        return round(late / early, 1) if early else None

    # Chart-ready series. The templates should never have to reshape data, and
    # colours are decided once here rather than in three different includes.
    eth_names = ", ".join(s["label"] for s in series if s["track"] == "ethiopia")
    afr_names = ", ".join(s["label"] for s in series if s["track"] == "africa")
    chart = {
        "aggregate": [
            {"label": f"Ethiopian languages ({eth_names})", "color": 1, "points": ethiopia},
            {"label": f"Comparison: {afr_names}", "color": 2, "points": africa},
        ],
        "ethiopian": [
            {"label": s["label"], "color": i + 1, "points": s["points"]}
            for i, s in enumerate(s for s in series if s["track"] == "ethiopia")
        ],
        "african": [
            {"label": s["label"], "color": i + 1, "points": s["points"]}
            for i, s in enumerate(s for s in series if s["track"] == "africa")
        ],
    }

    payload = {
        "generated": date.today().isoformat(),
        "chart": chart,
        "method": (
            "OpenAlex works matching a title/abstract search for the language name, "
            "intersected with the Natural language processing concept (C204321447). "
            "Counts are of indexed works, not of a curated bibliography. OpenAlex's "
            "coverage of the last year or two of any given period is uneven, so read "
            "the right-hand end of every line as a lower bound. The comparison between "
            "the lines is unaffected: both are counted the same way."
        ),
        "source_url": "https://openalex.org",
        "years": years,
        "series": series,
        "totals": {
            "ethiopia": ethiopia,
            "africa": africa,
            "ethiopia_total": sum(ethiopia),
            "africa_total": sum(africa),
            "ethiopia_growth": growth(ethiopia),
            "africa_growth": growth(africa),
            "last_year": years[-1],
            # How much of Ethiopian-language NLP is one language. This is the
            # number that actually characterises the field, and it is not
            # visible from the aggregate line.
            "top_language": max(
                (s for s in series if s["track"] == "ethiopia"),
                key=lambda s: s["total"],
            )["label"],
            "top_language_share": (
                round(
                    100
                    * max(s["total"] for s in series if s["track"] == "ethiopia")
                    / sum(s["total"] for s in series if s["track"] == "ethiopia"),
                    1,
                )
                if sum(s["total"] for s in series if s["track"] == "ethiopia") else None
            ),
            "ethiopia_share_now": (
                round(100 * ethiopia[-1] / (ethiopia[-1] + africa[-1]), 1)
                if (ethiopia[-1] + africa[-1]) else None
            ),
        },
        "milestones": load_curated("milestones.yml") or [],
    }

    if args.dry_run:
        print(f"\nEthiopia {payload['totals']['ethiopia_total']} · "
              f"Africa (comparison) {payload['totals']['africa_total']}")
        return 0

    write_generated("progress.yml", payload, "sync_progress.py", "milestones.yml")
    touch_meta("progress")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
