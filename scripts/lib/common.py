"""Shared helpers for the EthioNLP data-sync scripts.

Every sync script follows the same shape: read the community roster from
``_members/*.md``, call a public API, and write a machine-owned YAML file into
``_data/generated/``. Nothing here writes to a curated file, and nothing here
touches git, regenerating data is always safe, and the diff is the review.
"""

from __future__ import annotations

import http.client
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
MEMBERS_DIR = ROOT / "_members"
DATA = ROOT / "_data"
GENERATED = DATA / "generated"

CONTACT_EMAIL = "ethionlp@googlegroups.com"
USER_AGENT = f"ethionlp.github.io data sync (+https://ethionlp.github.io; mailto:{CONTACT_EMAIL})"

# Ethiopian and Ethiopia-adjacent languages, by ISO 639-3 where one exists.
# Used to tag artifacts and to decide whether an external resource is relevant.
ETHIOPIAN_LANGUAGES = {
    "am": "Amharic",
    "amh": "Amharic",
    "ti": "Tigrinya",
    "tir": "Tigrinya",
    "om": "Afaan Oromo",
    "orm": "Afaan Oromo",
    "so": "Somali",
    "som": "Somali",
    "aa": "Afar",
    "aar": "Afar",
    "sid": "Sidama",
    "wal": "Wolaytta",
    "gez": "Ge'ez",
    "har": "Harari",
    "gru": "Kistane",
    "sgw": "Sebat Bet Gurage",
    "xan": "Xamtanga",
    "awn": "Awngi",
    "kbr": "Kafa",
    "bcq": "Bench",
    "drs": "Gedeo",
    "hdy": "Hadiyya",
    "kcx": "Kachama-Ganjule",
    "nus": "Nuer",
    "anu": "Anuak",
    "muz": "Mursi",
    "tig": "Tigre",
    "byn": "Blin",
}

# Keywords that mark a resource as Ethiopian-language work even when it carries
# no language tag at all, which is the common case on the Hub.
ETHIOPIA_KEYWORDS = (
    "amharic", "tigrinya", "tigrigna", "oromo", "afaan", "ethiopia", "ethiopic",
    "geez", "ge'ez", "wolaytta", "wolaita", "sidama", "afar", "harari", "gurage",
    "awngi", "awgni", "khimtagne", "hadiyya", "kafa", "somali", "horn of africa",
)


# ─── HTTP ─────────────────────────────────────────────────────────────────────

def _request(url: str, headers: dict | None = None, timeout: int = 60):
    hdrs = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if headers:
        hdrs.update(headers)
    return urllib.request.Request(url, headers=hdrs)


def get_json(url: str, headers: dict | None = None, tries: int = 3, pause: float = 2.0):
    """GET and parse JSON, tolerating the transient failures these APIs have.

    Returns ``None`` rather than raising: a sync run that loses one source
    should still refresh everything else, and the caller decides whether a
    missing source is fatal.
    """
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(_request(url, headers), timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            if exc.code in (429, 500, 502, 503) and attempt < tries - 1:
                time.sleep(pause * (attempt + 2))
                continue
            warn(f"{exc.code} from {url}")
            return None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError,
                http.client.HTTPException, OSError) as exc:
            if attempt == tries - 1:
                warn(f"giving up on {url}: {exc}")
                return None
            time.sleep(pause * (attempt + 1))
    return None


def get_text(url: str, headers: dict | None = None, tries: int = 3, pause: float = 2.0):
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(_request(url, headers), timeout=60) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            if attempt == tries - 1:
                warn(f"{exc.code} from {url}")
                return None
            time.sleep(pause * (attempt + 1))
        except (urllib.error.URLError, TimeoutError,
                http.client.HTTPException, OSError) as exc:
            if attempt == tries - 1:
                warn(f"giving up on {url}: {exc}")
                return None
            time.sleep(pause * (attempt + 1))
    return None


# ─── Console ──────────────────────────────────────────────────────────────────

def info(msg: str) -> None:
    print(f"  {msg}")


def step(msg: str) -> None:
    print(f"\n\033[1m{msg}\033[0m" if sys.stdout.isatty() else f"\n{msg}")


def warn(msg: str) -> None:
    print(f"  ! {msg}", file=sys.stderr)


# ─── Members ──────────────────────────────────────────────────────────────────

FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.S)


def read_members() -> list[dict]:
    """Parse ``_members/*.md`` into dicts, with ``slug`` and ``body`` added."""
    members = []
    for path in sorted(MEMBERS_DIR.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        match = FRONT_MATTER.match(raw)
        if not match:
            warn(f"{path.name} has no front matter, skipping")
            continue
        try:
            data = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError as exc:
            warn(f"{path.name}: {exc}")
            continue
        data["slug"] = path.stem
        data["body"] = match.group(2).strip()
        data["_path"] = path
        members.append(data)
    return members


def member_name_index(members: list[dict]) -> dict[str, str]:
    """Map normalised author names (and a few variants) to member slugs."""
    index = {}
    for m in members:
        name = m.get("name") or ""
        if not name:
            continue
        index[norm_name(name)] = m["slug"]
        for alias in m.get("aliases") or []:
            index[norm_name(alias)] = m["slug"]
        # "Seid Muhie Yimam" also matches "Seid Yimam" and "S. M. Yimam".
        parts = name.split()
        if len(parts) > 2:
            index[norm_name(f"{parts[0]} {parts[-1]}")] = m["slug"]
    return index


def norm_name(name: str) -> str:
    n = (name or "").lower()
    n = re.sub(r"[^a-z\s]", " ", n)
    return " ".join(n.split())


# ─── Text helpers ─────────────────────────────────────────────────────────────

def norm_title(title: str) -> str:
    """Normalised title, used as the deduplication key across sources."""
    if not title:
        return ""
    # Semantic Scholar returns some titles with a literal backslash-n in them.
    # Stripping non-alphanumerics turns the backslash into a space and leaves
    # the "n" behind as a word, so "with\n Dynamic Vocabulary" normalised to
    # "with n dynamic vocabulary" and no longer matched the same paper from
    # another source. Undo the escape before the general strip.
    t = re.sub(r"\\[nrt]", " ", title.lower())
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return " ".join(t.split())


def squash_title(title: str) -> str:
    """norm_title with the word boundaries removed as well.

    A secondary deduplication key, for the same paper punctuated differently by
    two sources: "Multiword Expressions" against "Multi-word Expressions", or
    "ComplexWord Identification" against "Complex Word Identification". Both
    reduce to the same run of characters here, while any real difference in
    wording still produces a different key.
    """
    return norm_title(title).replace(" ", "")


def arxiv_from_doi(doi: str | None) -> str | None:
    """The arXiv id inside a DataCite arXiv DOI, if that is what this is.

    arXiv registers every submission as 10.48550/arXiv.<id>, so a record can
    carry the same identity in `doi` or in `arxiv` depending on which index it
    came from. Normalising the DOI back into an arXiv id lets the two forms
    deduplicate against each other.
    """
    if not doi:
        return None
    m = re.match(r"^10\.48550/arxiv\.(.+)$", clean_doi(doi) or "")
    return m.group(1) if m else None


def clean_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi.strip().lower())
    return doi or None


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")


def looks_ethiopian(*fields: str) -> bool:
    blob = " ".join(f for f in fields if f).lower()
    return any(k in blob for k in ETHIOPIA_KEYWORDS)


def language_names(codes) -> list[str]:
    """Map ISO codes to display names, dropping unknown and duplicate entries."""
    seen, out = set(), []
    for code in codes or []:
        name = ETHIOPIAN_LANGUAGES.get(str(code).lower())
        if name and name not in seen:
            seen.add(name)
            out.append(name)
    return out


# ─── Output ───────────────────────────────────────────────────────────────────

BANNER = (
    "# Generated by scripts/{script}, do not edit by hand.\n"
    "# Regenerate with `make sync`. Curated additions belong in\n"
    "# _data/{curated} instead.\n"
)


def write_generated(filename: str, payload, script: str, curated: str = "publications_manual.yml") -> None:
    GENERATED.mkdir(parents=True, exist_ok=True)
    path = GENERATED / filename
    body = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False, width=100)
    path.write_text(BANNER.format(script=script, curated=curated) + body, encoding="utf-8")
    info(f"wrote {path.relative_to(ROOT)}")


def touch_meta(source: str) -> None:
    """Record when each generated file was last refreshed, for the footer."""
    GENERATED.mkdir(parents=True, exist_ok=True)
    path = GENERATED / "meta.yml"
    meta = {}
    if path.exists():
        text = path.read_text(encoding="utf-8")
        meta = yaml.safe_load(re.sub(r"^#.*\n", "", text, flags=re.M)) or {}

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    meta["updated"] = now
    meta.setdefault("sources", {})[source] = now

    path.write_text(
        "# Generated by the sync scripts, do not edit by hand.\n"
        + yaml.safe_dump(meta, allow_unicode=True, sort_keys=True),
        encoding="utf-8",
    )


def load_curated(filename: str):
    path = DATA / filename
    if not path.exists():
        return []
    return yaml.safe_load(path.read_text(encoding="utf-8")) or []
