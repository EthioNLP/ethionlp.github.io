#!/usr/bin/env python3
"""Build the Ethiopian language catalogue into _data/generated/catalog.yml.

The catalogue answers three questions for every language spoken in Ethiopia:
who classifies it as what, how many people speak it, and how much NLP research
exists on it. Those three come from three different authorities, and the split
is deliberate:

  * Glottolog (CLDF release, CSV over HTTPS) owns the *list* and the
    *classification*. It is the only source consulted here that states, per
    languoid, which countries it is spoken in, so "is this a language of
    Ethiopia?" is Glottolog's answer, not ours. It also supplies coordinates,
    which Wikidata gives only patchily, and an endangerment grade (AES).
  * Wikidata owns the *numbers and the names*: ISO codes, speaker counts,
    writing system and endonym. (Region of origin is deliberately not
    collected any more -- see the note in the Wikidata step.)
    Glottolog has no speaker figures at all.
  * OpenAlex owns the *research volume*, and only for the top 15 by speakers, one API call per language, and the counts below that point are too small
    and too noisy to be worth the requests.

Nothing here is interpolated. A field whose source did not state it is written
as ``null``; there is no back-filling from a third source and no estimation.
That is why only about half the languages carry a speaker figure.

Three judgement calls are worth knowing about, because they change the count:

  1. Glottolog's "Bookkeeping" pseudo-family marks codes that duplicate or
     aggregate other codes. Gamo-Gofa-Dawro [gmo] is one: ISO split it into
     Gamo, Gofa and Dawro, all three of which are listed separately. Keeping it
     would double-count two million speakers, so Bookkeeping entries are dropped.
  2. Glottolog models ISO 639-3 macrolanguages as family nodes, not languages,
     so Oromo [orm], the most-spoken language in the country, would otherwise
     be absent, present only as West Central / Eastern / Borana-Arsi-Guji Oromo,
     none of which carry a speaker count. Macrolanguages are added back when
     Wikidata has a speaker figure for them that their members lack.
  3. Glottolog's top-level family for most of Ethiopia is "Afro-Asiatic", which
     puts Amharic and Afar in the same bucket and hides the one distinction that
     actually organises the country's languages. So ``family`` descends one
     level under Afro-Asiatic (giving Cushitic, Semitic) and stays at the top
     level everywhere else; ``family_top`` is always Glottolog's top node.

Usage:  python3 scripts/sync_catalog.py [--dry-run] [--top 15] [--no-openalex]
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import urllib.parse
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.common import (  # noqa: E402
    GENERATED,
    get_json,
    get_text,
    info,
    load_curated,
    step,
    touch_meta,
    warn,
    write_generated,
)

# ─── Sources ──────────────────────────────────────────────────────────────────

WDQS = "https://query.wikidata.org/sparql"
WD_API = "https://www.wikidata.org/w/api.php"
GLOTTOLOG_CLDF = "https://raw.githubusercontent.com/glottolog/glottolog-cldf/master/cldf"
OPENALEX = "https://api.openalex.org"

# OpenAlex is asked for a contact address so the request is not rate-limited
# into the anonymous pool. This is the address the site publishes for data work.
OPENALEX_MAILTO = "afriannotate@gmail.com"
NLP_CONCEPT = "C204321447"  # OpenAlex: Natural language processing

Q_ETHIOPIA = "Q115"
Q_LANGUAGE = "Q34770"

# Wikidata properties, named so the queries below read as prose.
P_ISO3, P_ISO1 = "P220", "P218"
P_NATIVE_LABEL = "P1705"
P_SPEAKERS = "P1098"
P_SCRIPT = "P282"
P_GLOTTOCODE = "P1394"
P_INDIGENOUS_TO = "P2341"

# OpenAlex searches on a bare language name. Where that name is also an English
# word, a personal name, a place, or simply not the spelling the NLP literature
# uses; the count is reported but marked unreliable rather than dropped, a
# wrong number that is labelled wrong is still evidence; a silent gap is not.
AMBIGUOUS_NAMES = {
    "Somali",           # the country and the ethnonym swamp the language
    "Afar",             # the region, the depression, the triangle
    "Kafa",             # the former province, and the coffee
    "Sidamo",           # the zone, and the coffee; the language is usually "Sidama"
    "Gedeo",            # the zone
    "Berta",            # a common given name and surname
    "Nuer",             # a common surname
    "Me'en",            # short, and the apostrophe tokenises unpredictably
    "Silt'e",           # ditto
    "Harari",           # the region, and a surname
    "Sebat Bet Gurage",  # the literature says "Gurage"; the full name matches nothing
    "Kambaata",         # spelled Kambata / Kembata / Kambaata in different papers
}


# ─── Glottolog ────────────────────────────────────────────────────────────────

def fetch_csv(name: str) -> list[dict]:
    """Fetch one CLDF table. These are plain CSV over HTTPS, no key, no paging."""
    raw = get_text(f"{GLOTTOLOG_CLDF}/{name}")
    if not raw:
        return []
    # values.csv carries whole bibliographies in single cells, well past the
    # default 128 KB field limit.
    csv.field_size_limit(10 ** 7)
    return list(csv.DictReader(io.StringIO(raw)))


def glottolog_tables() -> tuple[dict, dict, dict]:
    """Return (languoids by glottocode, classification paths, AES grades)."""
    languoids = {r["ID"]: r for r in fetch_csv("languages.csv")}
    info(f"Glottolog: {len(languoids)} languoids")

    classification, aes = {}, {}
    for row in fetch_csv("values.csv"):
        param = row["Parameter_ID"]
        if param == "classification":
            # A "/"-separated path of glottocodes from the top family downwards,
            # excluding the languoid itself.
            classification[row["Language_ID"]] = row["Value"]
        elif param == "aes":
            # Code_ID is e.g. "aes-not_endangered"; the bare Value is a 1-6 grade.
            aes[row["Language_ID"]] = row["Code_ID"]
    info(f"Glottolog: {len(classification)} classifications, {len(aes)} AES grades")
    return languoids, classification, aes


# Glottolog's AES grades, collapsed onto the three words the catalogue shows.
AES_STATUS = {
    "aes-not_endangered": "living",
    "aes-threatened": "endangered",
    "aes-shifting": "endangered",
    "aes-moribund": "endangered",
    "aes-nearly_extinct": "endangered",
    "aes-extinct": "extinct",
}


def families(languoids: dict, classification: dict, glottocode: str) -> tuple[str | None, str | None]:
    """(family, family_top) for a glottocode, see judgement call 3 in the docstring."""
    path = [languoids[g]["Name"] for g in classification.get(glottocode, "").split("/") if g in languoids]
    if not path:
        node = languoids.get(glottocode, {})
        # A top-level isolate has no path at all: it *is* its own family.
        if node.get("Is_Isolate") == "true":
            return f"{node.get('Name')} (isolate)", f"{node.get('Name')} (isolate)"
        return None, None
    top = path[0]
    family = path[1] if top == "Afro-Asiatic" and len(path) > 1 else top
    return family, top


# ─── Wikidata ─────────────────────────────────────────────────────────────────

def sparql(query: str) -> list[dict]:
    url = f"{WDQS}?query={urllib.parse.quote(query)}&format=json"
    data = get_json(url, headers={"Accept": "application/sparql-results+json"})
    if not data:
        warn("SPARQL query returned nothing")
        return []
    return data["results"]["bindings"]


def ethiopian_language_items() -> list[str]:
    """QIDs of everything Wikidata calls a language with country = Ethiopia.

    Kept deliberately narrow. Widening it (country of origin, indigenous to,
    located in an Ethiopian region) was tried and added exactly two items, both
    already present; the country statement is where Wikidata records this.
    Glottolog, not this query, decides what ends up in the catalogue; this is
    only the pool the numbers are drawn from.
    """
    rows = sparql(f"""
        SELECT ?item WHERE {{
          ?item wdt:P17 wd:{Q_ETHIOPIA} ; wdt:P31/wdt:P279* wd:{Q_LANGUAGE} .
        }}
    """)
    return sorted({r["item"]["value"].rsplit("/", 1)[-1] for r in rows})


def ethiopian_regions() -> dict[str, str]:
    """QID -> display name for Ethiopia's first-level administrative divisions.

    Used to filter "indigenous to" statements, which otherwise mix regions with
    countries, zones, mountains and ethnic groups.
    """
    rows = sparql(f"""
        SELECT ?r ?rLabel WHERE {{
          {{ wd:{Q_ETHIOPIA} wdt:P150 ?r }}
          UNION {{ ?r wdt:P31 wd:Q50815614 }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
    """)
    out = {}
    for r in rows:
        qid = r["r"]["value"].rsplit("/", 1)[-1]
        name = r["rLabel"]["value"]
        # "Amhara Region" and "South Ethiopia Regional State" read as noise in a
        # one-line list of places; the suffix carries no information here.
        for suffix in (" Regional State", " Region"):
            if name.endswith(suffix):
                name = name[: -len(suffix)]
        out[qid] = name
    return out


def wbgetentities(qids: list[str], props: str, languages: str | None = None) -> dict:
    """wbgetentities in batches of 50, which is the API's hard limit."""
    entities = {}
    for i in range(0, len(qids), 50):
        url = (f"{WD_API}?action=wbgetentities&format=json&props={props}"
               + (f"&languages={languages}" if languages else "")
               + "&ids=" + "|".join(qids[i:i + 50]))
        page = get_json(url)
        if page:
            entities.update(page.get("entities", {}))
    return entities


def claims(entity: dict, prop: str) -> list:
    return [s["mainsnak"]["datavalue"]["value"]
            for s in entity.get("claims", {}).get(prop, [])
            if s.get("mainsnak", {}).get("datavalue")]


def speakers(entity: dict) -> int | None:
    """The speaker count Wikidata itself considers current.

    Languages routinely carry several P1098 statements from different censuses.
    Wikidata marks the one it trusts as "preferred", so that rank wins; among
    equals the most recent point-in-time qualifier wins. Amharic, for instance,
    has 25,000,000 (2003) and 21,900,000 (2019, preferred), taking the larger
    number would be flattering and wrong.
    """
    statements = entity.get("claims", {}).get(P_SPEAKERS, [])
    if not statements:
        return None
    ranked = [s for s in statements if s["rank"] == "preferred"] \
        or [s for s in statements if s["rank"] == "normal"]
    if not ranked:
        return None

    def sort_key(s):
        qual = (s.get("qualifiers") or {}).get("P585")
        when = qual[0]["datavalue"]["value"]["time"] if qual else ""
        return (when, int(s["mainsnak"]["datavalue"]["value"]["amount"]))

    best = max(ranked, key=sort_key)
    return int(best["mainsnak"]["datavalue"]["value"]["amount"])


ETHIOPIC = range(0x1200, 0x1400)


def usable_endonym(text: str | None) -> str | None:
    """Keep an endonym only if it is written in Ethiopic or Latin script.

    Wikidata will happily return the Arabic, Cyrillic or Chinese name of an
    Ethiopian language; those are exonyms in another script and belong nowhere
    near a column headed "endonym".
    """
    if not text:
        return None
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return None
    ethiopic = sum(1 for c in letters if ord(c) in ETHIOPIC)
    latin = sum(1 for c in letters if ord(c) < 0x250)
    return text if (ethiopic + latin) == len(letters) else None


def endonym(entity: dict, labels: dict) -> str | None:
    """Prefer the explicit native label; fall back to the item's own-language label."""
    for native in claims(entity, P_NATIVE_LABEL):
        kept = usable_endonym(native.get("text") if isinstance(native, dict) else native)
        if kept:
            return kept
    # Wikidata labels are keyed by language code, so an item's label in its own
    # code is its endonym: Q28244's "am" label is አማርኛ.
    for code in claims(entity, P_ISO1) + claims(entity, P_ISO3):
        kept = usable_endonym((labels.get(code) or {}).get("value"))
        if kept:
            return kept
    return None


# ─── OpenAlex ─────────────────────────────────────────────────────────────────

def research_works(name: str) -> int | None:
    """Indexed NLP works mentioning the language name in title or abstract.

    Intersected with the Natural language processing concept, exactly as
    sync_progress.py does it, so the two dashboards are measured identically.
    """
    url = (f"{OPENALEX}/works"
           f"?filter=title_and_abstract.search:{urllib.parse.quote(name)},"
           f"concepts.id:{NLP_CONCEPT}&per-page=1&mailto={OPENALEX_MAILTO}")
    page = get_json(url)
    if not page:
        warn(f"OpenAlex: no response for {name!r}")
        return None
    return page.get("meta", {}).get("count")


# ─── Assembly ─────────────────────────────────────────────────────────────────

# ─── Presentation-time derivations ────────────────────────────────────────────
#
# Both of the following are computed here rather than in the templates. Liquid
# has no floating-point arithmetic, `divided_by` truncates, so a projection
# expressed in Liquid collapses every point into the top-left corner, and a
# name-based join written as a `where` filter silently misses any language whose
# Hugging Face tag spells it differently. Doing both in Python keeps the
# templates to lookups.

# The map's viewBox, and the geographic window it covers.
#
# The window is Ethiopia plus a margin, not the extent of the data. Several
# languages in the list are cross-border, Sudanese Arabic sits in Sudan,
# Borana-Arsi-Guji Oromo's point is in Kenya, Adamawa Fulfulde's is in Cameroon
#, and fitting the box to them would zoom the map out until Ethiopia itself
# was a smudge. Points outside the window are dropped from the map and counted,
# so the caption can say how many rather than quietly losing them.
MAP_W, MAP_H = 760, 620
MAP_WINDOW = {"lat_min": 2.8, "lat_max": 15.6, "lon_min": 32.6, "lon_max": 48.4}

# Hugging Face language tags do not always match Glottolog's preferred name.
ARTIFACT_ALIASES = {
    "afaan oromo": "Oromo",
    "oromo": "Oromo",
    "amharic": "Amharic",
    "tigrinya": "Tigrinya",
    "somali": "Somali",
    "ge'ez": "Geez",
    "geez": "Geez",
    "wolaytta": "Wolaytta",
    "wolaita": "Wolaytta",
    "sidama": "Sidamo",
    "sidamo": "Sidamo",
    "afar": "Afar",
}


# Ethiopia's outline, so the scatter reads as a map rather than a chart. Natural
# Earth's 1:110m boundaries are public domain and small enough to bake straight
# into the generated file as an SVG path.
BORDER_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/"
    "geojson/ne_110m_admin_0_countries.geojson"
)
BORDER_COUNTRIES = ("Ethiopia",)
# Drawn behind Ethiopia in a lighter tone, for orientation.
BORDER_NEIGHBOURS = (
    "Eritrea", "Djibouti", "Somalia", "Somaliland", "Kenya", "South Sudan", "Sudan",
)


def border_paths(box: dict) -> dict:
    """Country outlines as SVG path data, in the same projection as the points."""
    raw = get_text(BORDER_URL)
    if not raw:
        warn("could not fetch country boundaries; the map will have no outline")
        return {}

    try:
        collection = json.loads(raw)
    except ValueError:
        warn("country boundary file was not valid JSON")
        return {}

    lon_span = box["lon_max"] - box["lon_min"]
    lat_span = box["lat_max"] - box["lat_min"]

    def to_px(lon, lat):
        return (
            round((lon - box["lon_min"]) / lon_span * MAP_W, 1),
            round((box["lat_max"] - lat) / lat_span * MAP_H, 1),
        )

    def rings(geometry):
        if geometry.get("type") == "Polygon":
            return geometry["coordinates"]
        if geometry.get("type") == "MultiPolygon":
            return [ring for poly in geometry["coordinates"] for ring in poly]
        return []

    def to_path(geometry):
        parts = []
        for ring in rings(geometry):
            points = [to_px(lon, lat) for lon, lat in ring]
            if len(points) < 3:
                continue
            head = points[0]
            body = " ".join(f"L{x} {y}" for x, y in points[1:])
            parts.append(f"M{head[0]} {head[1]} {body}Z")
        return " ".join(parts)

    out = {}
    neighbours = []
    for feature in collection.get("features", []):
        name = (feature.get("properties") or {}).get("NAME") or ""
        geometry = feature.get("geometry") or {}
        if name in BORDER_COUNTRIES:
            out["country"] = to_path(geometry)
        elif name in BORDER_NEIGHBOURS:
            path = to_path(geometry)
            if path:
                neighbours.append(path)

    if neighbours:
        out["neighbours"] = " ".join(neighbours)
    if "country" not in out:
        warn("Ethiopia was not found in the boundary file")

    info(f"borders: Ethiopia + {len(neighbours)} neighbours")
    return out


def project(languages: list[dict]) -> dict:
    """Add integer x/y pixel coordinates for the map, in place."""
    box = MAP_WINDOW
    lon_span = box["lon_max"] - box["lon_min"]
    lat_span = box["lat_max"] - box["lat_min"]
    plotted = outside = missing = 0

    for lang in languages:
        lat, lon = lang.get("lat"), lang.get("lon")
        if lat is None or lon is None:
            lang["map_x"] = lang["map_y"] = lang["map_r"] = None
            missing += 1
            continue

        if not (box["lat_min"] <= lat <= box["lat_max"]
                and box["lon_min"] <= lon <= box["lon_max"]):
            lang["map_x"] = lang["map_y"] = lang["map_r"] = None
            outside += 1
            continue

        plotted += 1
        # Equirectangular; at the scale of one country the distortion is far
        # smaller than the uncertainty in a Glottolog point coordinate.
        lang["map_x"] = round((lang["lon"] - box["lon_min"]) / lon_span * MAP_W, 1)
        lang["map_y"] = round((box["lat_max"] - lang["lat"]) / lat_span * MAP_H, 1)

        # Radius band, so the templates do not have to bucket by hand.
        n = lang.get("speakers") or 0
        lang["map_r"] = 13 if n > 5_000_000 else 9 if n > 1_000_000 else 6 if n > 100_000 else 4.5 if n else 3

    info(f"map: {plotted} plotted, {outside} outside the window, {missing} without coordinates")
    return dict(box, w=MAP_W, h=MAP_H, plotted=plotted, outside=outside, missing=missing)


def scale_bars(languages: list[dict]) -> None:
    """Add 0-100 bar widths for speakers and papers, log-scaled, in place.

    Both quantities span too many orders of magnitude for a linear bar to say
    anything: speakers run from 12 to 24 million, papers from 0 to 1,246. On a
    linear scale Amharic is the only visible mark and everything else is a
    hairline. A log scale shows the shape of the distribution instead, which is
    the actual point of the column.

    Liquid has no logarithm, so this is computed here and the template only
    places a width.
    """
    import math

    for field, out in (("speakers", "speakers_bar"), ("research_works", "papers_bar")):
        values = [l[field] for l in languages if l.get(field)]
        if not values:
            for l in languages:
                l[out] = 0
            continue
        # Normalised across the observed range, not from zero. Dividing by the
        # maximum alone leaves the smallest language at about 70% of the bar,
        # because log10(159,000) is most of log10(24,000,000); anchoring the
        # bottom of the scale at the smallest observed value spreads the data
        # over the whole bar instead.
        lo, hi = math.log10(min(values)), math.log10(max(values))
        span = (hi - lo) or 1.0
        for l in languages:
            v = l.get(field)
            if not v:
                # A recorded zero keeps a sliver so it reads as measured rather
                # than missing; a missing value gets nothing at all.
                l[out] = 2 if v == 0 else 0
                continue
            l[out] = max(4, round((math.log10(v) - lo) / span * 100))


def attach_artifacts(languages: list[dict]) -> int:
    """Join the Hugging Face per-language counts onto the catalogue.

    Returns the number of languages that carry at least one artifact.
    """
    hf = GENERATED / "huggingface.yml"
    if not hf.exists():
        warn("huggingface.yml not found, run sync_huggingface.py first; "
             "coverage will show as zero")
        for lang in languages:
            lang["models"] = lang["datasets"] = 0
        return 0

    with hf.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    counts: dict[str, dict] = {}
    for entry in data.get("per_language") or []:
        raw = entry.get("name")
        name = ARTIFACT_ALIASES.get((raw or "").strip().lower(), raw)
        bucket = counts.setdefault(name, {"models": 0, "datasets": 0, "names": []})
        bucket["models"] += entry.get("models") or 0
        bucket["datasets"] += entry.get("datasets") or 0
        # The names the artifacts themselves use, kept so a template can list
        # the individual models and datasets. Templates cannot apply the alias
        # table, so joining on the catalogue name alone silently drops every
        # language the two sources spell differently, which here is Oromo
        # (recorded as "Afaan Oromo") and Geez ("Ge'ez").
        if raw and raw not in bucket["names"]:
            bucket["names"].append(raw)

    matched = set()
    for lang in languages:
        found = counts.get(lang["name"])
        if not found:
            # Try the alias table from the other direction, and the ISO code.
            key = ARTIFACT_ALIASES.get(lang["name"].lower())
            found = counts.get(key) if key else None
        lang["models"] = (found or {}).get("models", 0)
        lang["datasets"] = (found or {}).get("datasets", 0)
        lang["artifact_names"] = (found or {}).get("names") or [lang["name"]]
        # Every spelling that resolves to this language, lowercased, so a
        # template can join on it with `contains` after a `| downcase`.
        # artifact_names alone is not enough: it records only the spellings
        # Hugging Face actually emitted, while expertise.yml takes its names
        # from publications and repositories. "Sidama" for Sidamo appears in
        # one and not the other, which is how member profiles ended up linking
        # to /languages/#sidama, an anchor that does not exist.
        match = {lang["name"].lower()}
        match.update(n.lower() for n in lang["artifact_names"])
        match.update(a for a, target in ARTIFACT_ALIASES.items()
                     if target == lang["name"])
        lang["match_names"] = sorted(match)
        if found:
            matched.add(lang["name"])

    unmatched = set(counts) - matched
    if unmatched:
        warn("no catalogue entry for these Hugging Face languages: "
             + ", ".join(sorted(unmatched))
             + ", add them to ARTIFACT_ALIASES")

    return len(matched)


def build(args) -> dict:
    step("Glottolog CLDF, the language list, classification and coordinates")
    languoids, classification, aes = glottolog_tables()
    if not languoids:
        warn("Glottolog unavailable; refusing to write a catalogue without it")
        return {}

    # Glottolog's Countries column is a ";"-separated list of ISO 3166 codes.
    ethiopia = [r for r in languoids.values()
                if "ET" in (r.get("Countries") or "").split(";") and r["Level"] == "language"]
    info(f"{len(ethiopia)} language-level languoids listed for Ethiopia")

    # Glottolog's country field is occasionally wrong, and a wrong entry here
    # inflates the denominator the whole site is measured against. Each
    # exclusion needs a reason, and only clear errors qualify: a cross-border
    # language with speakers inside Ethiopia (Nuer, Somali, Sudanese Arabic)
    # belongs in the catalogue and is not listed here.
    excluded = {
        "adam1253": "Adamawa Fulfulde: spoken in Cameroon, Nigeria and Chad, "
                    "some 4,000 km away. The Ethiopian attribution is not credible.",
    }
    for code, reason in excluded.items():
        hit = next((r for r in ethiopia if r["ID"] == code), None)
        if hit:
            ethiopia.remove(hit)
            info(f"excluded {hit['Name']}: {reason}")

    dropped = [r for r in ethiopia if families(languoids, classification, r["ID"])[1] == "Bookkeeping"]
    ethiopia = [r for r in ethiopia if r not in dropped]
    for r in dropped:
        info(f"dropped {r['Name']} [{r['ISO639P3code']}], Glottolog Bookkeeping (duplicate code)")

    step("Wikidata, ISO codes, speakers, scripts, endonyms")
    qids = ethiopian_language_items()
    info(f"{len(qids)} language items with country = Ethiopia")
    entities = wbgetentities(qids, "labels|claims", languages="en")
    all_labels = wbgetentities(qids, "labels")  # every language, for endonyms
    regions = ethiopian_regions()
    info(f"{len(regions)} administrative regions")

    # One pass to collect every QID referenced by a script or "indigenous to"
    # statement, so their English labels can be fetched in one batch.
    referenced = set()
    for entity in entities.values():
        for prop in (P_SCRIPT, P_INDIGENOUS_TO):
            referenced.update(v["id"] for v in claims(entity, prop) if isinstance(v, dict))
    ref_labels = {q: e.get("labels", {}).get("en", {}).get("value")
                  for q, e in wbgetentities(sorted(referenced), "labels", languages="en").items()}

    by_iso, by_glottocode = {}, {}
    for qid, entity in entities.items():
        for code in claims(entity, P_ISO3):
            by_iso[code] = (qid, entity)
        for code in claims(entity, P_GLOTTOCODE):
            by_glottocode[code] = (qid, entity)

    def entry(glottocode: str, name: str, iso: str | None,
              match: tuple[str, dict] | None) -> dict:
        node = languoids.get(glottocode, {})
        qid, entity = match if match else (None, {})
        family, family_top = families(languoids, classification, glottocode)
        scripts = [ref_labels.get(v["id"]) for v in claims(entity, P_SCRIPT) if isinstance(v, dict)]
        # Not published. P_INDIGENOUS_TO points at whatever unit Wikidata
        # happens to record -- often a zone or an ethnic group -- and keeping
        # only the first-level divisions collapsed those onto the wrong region
        # wholesale: Sidaama, Hadiyya, Kafa, Gedeo, Dawro, Hamer-Banna and
        # eleven more all came out as "Oromia", and Sheko as "Gambela", while
        # Sidama, Central Ethiopia, South West Ethiopia, South Ethiopia and
        # SNNPR never appeared once across 100 languages. Regional attribution
        # in Ethiopia is not a detail to get wrong, and there is no way to
        # filter this into correctness -- the underlying statement is simply
        # not the fact the field claimed. Restore it only with a per-language
        # source somebody has checked.
        homelands = []
        count = speakers(entity) if entity else None

        def coord(field):
            try:
                return round(float(node.get(field)), 4)
            except (TypeError, ValueError):
                return None

        return {
            "name": name,
            "endonym": endonym(entity, all_labels.get(qid, {})) if entity else None,
            "iso": iso or None,
            "glottocode": glottocode,
            "family": family,
            "family_top": family_top,
            "script": next((s for s in scripts if s), None),
            "speakers": count,
            "speakers_source": "Wikidata" if count is not None else None,
            "status": AES_STATUS.get(aes.get(glottocode)),
            "regions": homelands or None,
            "lat": coord("Latitude"),
            "lon": coord("Longitude"),
            "research_works": None,   # filled in below, top-N only
            "count_reliable": None,
            "wikidata": qid,
        }

    languages = [
        entry(r["ID"], r["Name"], r["ISO639P3code"],
              by_iso.get(r["ISO639P3code"]) or by_glottocode.get(r["ID"]))
        for r in ethiopia
    ]
    listed = {lang["glottocode"] for lang in languages}
    # Guarded on the ISO code as well as the glottocode, because a fair number
    # of Wikidata items carry a stale P1394: Kambaata [ktb] points at the
    # Kambaataic *family* node, not at the language, and would otherwise be
    # admitted a second time by the macrolanguage rule below.
    listed_iso = {lang["iso"] for lang in languages if lang["iso"]}

    # Judgement call 2: put ISO macrolanguages back, but only where doing so
    # adds a speaker figure rather than duplicating one.
    for qid, entity in entities.items():
        iso = claims(entity, P_ISO3)
        code = claims(entity, P_GLOTTOCODE)
        if not iso or not code or code[0] in listed or iso[0] in listed_iso:
            continue
        node = languoids.get(code[0])
        if not node or node["Level"] != "family" or speakers(entity) is None:
            continue
        # The family node must actually sit over Ethiopian languages, or this
        # would readmit any macrolanguage that happens to be spoken here.
        if not any(code[0] in classification.get(g, "").split("/") for g in listed):
            continue
        name = entity.get("labels", {}).get("en", {}).get("value") or node["Name"]
        macro = entry(code[0], name, iso[0], (qid, entity))

        # Fold the macrolanguage's members into it rather than listing both.
        # Glottolog has Oromo's three varieties as separate languages, and
        # Wikidata has the macrolanguage; keeping all four counted Oromo four
        # times, once with the full 24-million speaker figure and once per
        # variety. The members are recorded on the macrolanguage so nothing is
        # lost, and the ISO codes stay searchable.
        members = [
            lang for lang in languages
            if code[0] in classification.get(lang["glottocode"], "").split("/")
        ]
        if members:
            macro["includes"] = sorted(
                {m["name"] for m in members}
            )
            macro["includes_iso"] = sorted({m["iso"] for m in members if m["iso"]})
            # Endangerment is recorded against the varieties, not against the
            # macrolanguage, so folding left Oromo with no status at all, and
            # every count of "living or endangered" then quietly excluded the
            # largest language in the country. A macrolanguage is as alive as
            # its healthiest variety, so inherit that.
            if not macro.get("status"):
                rank = ["living", "endangered", "extinct"]
                have = [m.get("status") for m in members if m.get("status")]
                if have:
                    macro["status"] = min(
                        have, key=lambda s: rank.index(s) if s in rank else len(rank)
                    )
            for m in members:
                languages.remove(m)
            info(f"folded {len(members)} varieties into {name}: "
                 + ", ".join(m["name"] for m in members))

        languages.append(macro)
        info(f"re-added macrolanguage {name} [{iso[0]}], {speakers(entity):,} speakers")

    # Curated additions, if a maintainer ever needs one the sources do not carry.
    for extra in load_curated("catalog_manual.yml") or []:
        languages.append(extra)
        info(f"curated addition: {extra.get('name')}")

    # Sorted by speakers descending, unknowns last, then alphabetically so that
    # two runs of the script produce byte-identical files.
    languages.sort(key=lambda l: (l["speakers"] is None, -(l["speakers"] or 0), l["name"]))

    if not args.no_openalex:
        step(f"OpenAlex, research volume for the top {args.top} by speakers")
        for lang in languages[:args.top]:
            count = research_works(lang["name"])
            lang["research_works"] = count
            lang["count_reliable"] = None if count is None else lang["name"] not in AMBIGUOUS_NAMES
            flag = "" if lang["count_reliable"] else "  (name is ambiguous, treat as noise)"
            info(f"{lang['name']:<20} {str(count):>6} works{flag}")

    family_counts = {}
    for lang in languages:
        if lang["family"]:
            family_counts[lang["family"]] = family_counts.get(lang["family"], 0) + 1

    scale_bars(languages)
    map_box = project(languages)
    map_box.update(border_paths(map_box))
    covered = attach_artifacts(languages)

    return {
        "generated": date.today().isoformat(),
        "sources": [
            {"name": "Glottolog 5.x (CLDF)", "url": "https://glottolog.org/"},
            {"name": "Wikidata", "url": "https://query.wikidata.org/"},
            {"name": "OpenAlex", "url": "https://openalex.org"},
        ],
        "method": (
            "The list is every languoid Glottolog records at language level with "
            "Ethiopia among its countries, minus Glottolog's Bookkeeping codes "
            "(duplicate or superseded ISO codes) and plus any ISO 639-3 "
            "macrolanguage Glottolog models as a family node whose members are "
            "in the list; classification, coordinates and endangerment status "
            "are Glottolog's, while ISO codes, endonyms, writing systems, "
            "and speaker counts come from Wikidata, where the speaker "
            "figure is the statement Wikidata itself ranks as preferred (most "
            "recent census where one is dated) and counts first-language "
            "speakers unless Wikidata's own statement says otherwise; it is "
            "not a population figure, the totals double-count multilingual "
            "speakers, and roughly half the languages have no published count "
            "at all and are written as null rather than estimated."
        ),
        "totals": {
            "languages": len(languages),
            "with_artifacts": covered,
            "families": len(family_counts),
            "with_iso": sum(1 for l in languages if l["iso"]),
            # A recorded zero (Weyto) is a figure, not a missing value.
            "with_speakers": sum(1 for l in languages if l["speakers"] is not None),
            "speakers_total": sum(l["speakers"] or 0 for l in languages) or None,
        },
        "map": map_box,
        "families": [{"name": n, "count": c}
                     for n, c in sorted(family_counts.items(), key=lambda kv: (-kv[1], kv[0]))],
        "languages": languages,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true",
                        help="fetch and summarise, but do not write the file")
    parser.add_argument("--top", type=int, default=15,
                        help="how many languages get an OpenAlex research count")
    parser.add_argument("--no-openalex", action="store_true",
                        help="skip the research counts (useful when iterating)")
    args = parser.parse_args()

    payload = build(args)
    if not payload:
        return 1

    totals = payload["totals"]
    step("Summary")
    info(f"{totals['languages']} languages, {totals['families']} families, "
         f"{totals['with_iso']} with ISO 639-3, {totals['with_speakers']} with a speaker count")

    if args.dry_run:
        for lang in payload["languages"][:10]:
            info(f"{lang['name']:<24}{str(lang['speakers'] or ''):>12}  {lang['family']}")
        return 0

    write_generated("catalog.yml", payload, "sync_catalog.py", "catalog_manual.yml")
    touch_meta("catalog")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
