#!/usr/bin/env python3
"""Generate the EthioNLP logo: a stacked wordmark and a badge.

The logo is the name, set in the site's display face on two lines:

    Ethio
    [NLP]

**Ethio** sits on the first line. **NLP** sits on the second, letter-spaced
until it is exactly as wide as the word above it, and knocked out of a solid
bar. Two devices are doing the work there and both are deliberate.

The width match is the reason the thing looks drawn rather than typed. Two
stacked words of unequal length read as a line break; two of equal length read
as a block, and the eye takes the block as one object. The tracking is solved
numerically (see `track_to`), not eyeballed, so it stays exact if the type size
or the weight ever changes.

The knockout is a hole, not white paint: the bar and the letters are a single
path with `fill-rule="evenodd"`, so the page shows through the letterforms.
That means the mark needs no second colour, inverts for free on the dark theme,
and cannot go wrong on a coloured ground.

Why there is no separate icon. Four were tried and each failed for a reason
worth recording: a Ge'ez letterform (ኢ) only ever spells the country's initial
and reads as an abstract squiggle to anyone outside the script; four dots in a
rounded square read as a die; a five-node network read as a generic tech
graphic, and stretched wide enough to hold the name it read as an envelope; the
Ethiopic word separator ፡ alone is two dots, which at favicon size is a colon.
The compact form is instead the same stacked construction inside a rounded
square: the badge. It is the logo, smaller, so there is nothing extra to learn.

Everything is baked to outlines, so neither form depends on a web font having
loaded, which matters most off-site: a social card, or someone's slide deck.

    python3 scripts/build_logo.py            # write the wordmark, badge, icons
    python3 scripts/build_logo.py --check    # print the paths, write nothing
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.common import ROOT, info, step, warn  # noqa: E402

ETHIOPIC_URL = (
    "https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/"
    "fonts/NotoSansEthiopic/hinted/ttf/NotoSansEthiopic-SemiBold.ttf"
)
SERIF_URL = (
    "https://raw.githubusercontent.com/google/fonts/main/ofl/sourceserif4/"
    "SourceSerif4%5Bopsz%2Cwght%5D.ttf"
)
SANS_URL = (
    "https://raw.githubusercontent.com/google/fonts/main/ofl/sourcesans3/"
    "SourceSans3%5Bwght%5D.ttf"
)
CACHE = Path(__file__).resolve().parent / ".cache"
ETHIOPIC = CACHE / "NotoSansEthiopic-SemiBold.ttf"
SERIF = CACHE / "SourceSerif4.ttf"
SANS = CACHE / "SourceSans3.ttf"

GREEN = "#1b5e43"
GOLD = "#b8860f"
PAPER = "#fcfbf9"

TOP = "Ethio"
BOTTOM = "NLP"

SIZE = 30.0          # nominal type size, in the logo's own units
LEAD = 0.90          # baseline-to-baseline, as a fraction of SIZE
BAR_TOP = 0.76       # bar edges relative to the second baseline
BAR_BOTTOM = 0.09
BLEED = 0.09         # how far the bar runs past the word above it
PAD = 0.20           # padding around the ink

# The trend line: climbs in from the lower left, runs straight through to
# divide the two words, then climbs again under an arrowhead. Low-resource at
# the left, resources accumulating towards the right. Fractions of SIZE.
#
# The middle segment is deliberately flat. It is doing a typographic job as
# well as a rhetorical one, dividing Ethio from NLP, and a divider that wanders
# reads as a mistake rather than as a chart.
# The divider sits in the gap between Ethio's baseline and NLP's cap height,
# not on NLP's capitals. At 0.72 it cut straight through the N, L and P.
DIVIDER = 0.82       # above NLP's baseline, as a fraction of SIZE
LEAD_RUN = 0.40      # the horizontal length of the first climb
RISE = 0.72          # how high the arrow climbs above the divider
RUN = 0.50           # how far right it travels while climbing
HEAD = 0.21          # arrowhead length

LOGO_INCLUDE = ROOT / "_includes" / "logo.html"
LOCKUP_INCLUDE = ROOT / "_includes" / "lockup.html"
FAVICON = ROOT / "assets" / "img" / "favicon.svg"
VARIANTS = ROOT / "assets" / "img" / "logo"
IMG = ROOT / "assets" / "img"

# Raster icons the head and the manifest ask for, each from the form that
# survives its size: the tile in the tab bar, the full badge on a home screen.
RASTERS = [
    ("favicon-32.png", 32, "tile"),
    ("apple-touch-icon.png", 180, "badge"),
    ("icon-512.png", 512, "badge"),
]


def fetch(url: str, dest: Path, label: str) -> Path:
    if dest.exists():
        return dest
    CACHE.mkdir(parents=True, exist_ok=True)
    step(f"Downloading {label} (SIL OFL)")
    req = urllib.request.Request(url, headers={"User-Agent": "ethionlp.github.io"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        dest.write_bytes(resp.read())
    info(f"cached at {dest.relative_to(ROOT)}")
    return dest


_FONTS: dict[str, object] = {}


def fonts():
    from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont

    if "serif" not in _FONTS:
        serif = TTFont(fetch(SERIF_URL, SERIF, "Source Serif 4"))
        # Pin the variable axes to the weight and optical size the site sets
        # for display type, so the logo matches the headings beside it.
        _FONTS["serif"] = instantiateVariableFont(serif, {"wght": 600, "opsz": 32})
        _FONTS["ethiopic"] = TTFont(fetch(ETHIOPIC_URL, ETHIOPIC, "Noto Sans Ethiopic"))
    return _FONTS["serif"], _FONTS["ethiopic"]


def sans(weight: int = 400):
    """Source Sans 3 at one weight. The card sets body copy in it, as the site does."""
    from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont

    key = f"sans{weight}"
    if key not in _FONTS:
        _FONTS[key] = instantiateVariableFont(
            TTFont(fetch(SANS_URL, SANS, "Source Sans 3")), {"wght": weight}
        )
    return _FONTS[key]


def draw(font, text: str, size: float, x: float = 0.0, y: float = 0.0,
         track: float = 0.0) -> str:
    """Text as SVG path data, drawn from (x, y) with `track` between letters."""
    from fontTools.misc.transform import Transform
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen

    glyphs, cmap = font.getGlyphSet(), font.getBestCmap()
    upem, hmtx = font["head"].unitsPerEm, font["hmtx"]
    scale = size / upem

    pen = SVGPathPen(glyphs)
    cursor = x
    last = len(text) - 1
    for i, ch in enumerate(text):
        name = cmap.get(ord(ch))
        if not name:
            warn(f"no glyph for {ch!r}")
            continue
        # Font units are y-up and SVG is y-down, hence the negative y scale.
        glyphs[name].draw(TransformPen(pen, Transform(scale, 0, 0, -scale, cursor, y)))
        # Tracking goes between letters, never after the last one: a trailing
        # space would make the block wider than the word it is matching.
        cursor += hmtx[name][0] * scale + (track if i < last else 0.0)
    return pen.getCommands()


def ink(*paths: str) -> tuple[float, float, float, float]:
    pts = []
    for d in paths:
        pts += [(float(a), float(b))
                for a, b in re.findall(r"(-?\d+\.?\d*)\s+(-?\d+\.?\d*)", d)]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def track_to(font, text: str, size: float, target: float, y: float = 0.0) -> str:
    """Letter-space `text` until its inked width is `target`, left edge at 0.

    Bisection rather than arithmetic because the answer is set by the ink, and
    the side bearings of the first and last letters are not the same. Fifty
    rounds over this interval settles far below a thousandth of a unit, which
    is invisible at any size the logo is ever drawn.
    """
    lo, hi = -size * 0.2, size * 0.9
    for _ in range(50):
        mid = (lo + hi) / 2
        x0, _, x1, _ = ink(draw(font, text, size, 0.0, y, mid))
        if x1 - x0 < target:
            lo = mid
        else:
            hi = mid
    track = (lo + hi) / 2
    x0, _, _, _ = ink(draw(font, text, size, 0.0, y, track))
    return draw(font, text, size, -x0, y, track)


def rounded_rect(x: float, y: float, w: float, h: float, r: float) -> str:
    """A rounded rectangle as path data, so it can share a path with the type."""
    r = min(r, w / 2, h / 2)
    return (
        f"M{x + r:.2f} {y:.2f}H{x + w - r:.2f}A{r:.2f} {r:.2f} 0 0 1 {x + w:.2f} {y + r:.2f}"
        f"V{y + h - r:.2f}A{r:.2f} {r:.2f} 0 0 1 {x + w - r:.2f} {y + h:.2f}"
        f"H{x + r:.2f}A{r:.2f} {r:.2f} 0 0 1 {x:.2f} {y + h - r:.2f}"
        f"V{y + r:.2f}A{r:.2f} {r:.2f} 0 0 1 {x + r:.2f} {y:.2f}Z"
    )


def stacked(size: float = SIZE) -> tuple[str, str, float, float, float]:
    """The two lines, left edges aligned and equal in width.

    Returns (top, bottom, width, top-of-ink, second-baseline).
    """
    serif, _ = fonts()
    x0, y0, x1, _ = ink(draw(serif, TOP, size))
    width = x1 - x0
    top = draw(serif, TOP, size, -x0)
    baseline = size * LEAD
    bottom = track_to(serif, BOTTOM, size, width, baseline)
    return top, bottom, width, y0, baseline


def trend(x: float, y: float, size: float) -> str:
    """The rule and its arrow, as one path.

    A straight line, because it is doing a typographic job as well as a
    rhetorical one: it divides Ethio from NLP. The climb happens after the
    words, so nothing crosses a letterform.
    """
    import math

    th = size * 0.075
    rise, run, head = size * RISE, size * RUN, size * HEAD
    lead = size * LEAD_RUN
    # The climb starts level with the foot of the N rather than partway up it,
    # so the mark has a flat bottom edge and the line reads as coming up from
    # the baseline. Derived, not a constant, so it follows DIVIDER.
    drop = size * DIVIDER - th / 2

    def bar(ax, ay, bx, by):
        """A segment as a rotated rectangle, so joins stay square."""
        ang = math.atan2(by - ay, bx - ax)
        px, py = -math.sin(ang) * th / 2, math.cos(ang) * th / 2
        return (f"M{ax + px:.2f} {ay + py:.2f}L{bx + px:.2f} {by + py:.2f}"
                f"L{bx - px:.2f} {by - py:.2f}L{ax - px:.2f} {ay - py:.2f}Z")

    cy = y + th / 2
    # Three strokes, low to high: the climb that starts to the left of the N,
    # the divider running under Ethio and over NLP, and the climb to the arrow
    # added below. A fourth, flat, stroke before the climb made it four lines
    # and read as a stray tick.
    rule = bar(-lead, cy + drop, 0.0, cy) + bar(0.0, cy, x, cy)

    ang = math.atan2(-rise, run)
    dx, dy = math.cos(ang), math.sin(ang)
    ex, ey = x + run, cy - rise
    shaft = bar(x, cy, ex, ey)
    a = (ex + dx * head, ey + dy * head)
    b = (ex - dy * head * 0.62 - dx * head * 0.1, ey + dx * head * 0.62 - dy * head * 0.1)
    c = (ex + dy * head * 0.62 - dx * head * 0.1, ey - dx * head * 0.62 - dy * head * 0.1)
    arrowhead = f"M{a[0]:.2f} {a[1]:.2f}L{b[0]:.2f} {b[1]:.2f}L{c[0]:.2f} {c[1]:.2f}Z"
    return rule + shaft + arrowhead


def lockup(fill: str, knockout: str | None) -> tuple[str, float, float]:
    """The wordmark, with the trend line dividing its two lines.

    `knockout` is kept in the signature for the flat exports, which still want
    an explicit second colour; the divider is now a rule rather than a filled
    bar, so nothing is cut out of anything.
    """
    top, bottom, width, y0, baseline = stacked()
    pad = SIZE * PAD
    rule_y = baseline - SIZE * DIVIDER
    line = trend(width, rule_y, SIZE)

    # One fill throughout. The knockout the bar used to need is gone with the
    # bar; a rule does the dividing and the arrow carries the meaning.
    body = (f'<path d="{top}" fill="{fill}"/><path d="{bottom}" fill="{fill}"/>'
            f'<path d="{line}" fill="{fill}"/>')

    # Measure the whole mark, not just the type. The line starts to the left of
    # x=0 and climbs above it, so framing on the words alone clipped the flat
    # segment clean off the left edge of the viewBox.
    x_min, _, x_max, _ = ink(top + bottom + line)
    apex = rule_y + SIZE * 0.075 / 2 - SIZE * RISE - SIZE * HEAD
    y_min = min(y0, apex)
    _, _, _, y_max = ink(bottom)
    w = (x_max - x_min) + 2 * pad
    h = (y_max - y_min) + 2 * pad
    # The transform negates y, so the top of the ink is the minimum, not the
    # maximum; shifting by -y_min brings it down to the padding.
    return (f'<g transform="translate({pad - x_min:.2f} {pad - y_min:.2f})">'
            f'{body}</g>', w, h)


def badge(ground: str, first: str, second: str) -> tuple[str, float]:
    """The compact form: the same two lines inside a rounded square."""
    size = SIZE * 0.80
    top, bottom, width, y0, baseline = stacked(size)
    height = (baseline + size * BAR_BOTTOM) - y0
    side = max(width, height) + 2 * (size * 0.34)
    body = (
        f'<path d="{rounded_rect(0, 0, side, side, side * 0.19)}" fill="{ground}"/>'
        f'<g transform="translate({(side - width) / 2:.2f} '
        f'{(side - height) / 2 - y0:.2f})">'
        f'<path d="{top}" fill="{first}"/><path d="{bottom}" fill="{second}"/></g>'
    )
    return body, side


def tile(ground: str, letters: str) -> tuple[str, float]:
    """The smallest form: the second line alone, filling a rounded square.

    A favicon is drawn at 16 to 32 pixels. Eight letters on two lines do not
    survive that: at 32 the first line is three pixels tall and turns to mush.
    So the small icon keeps the half of the mark that carries the field, which
    is also the half with the distinctive treatment: NLP in its bar. It is a
    crop of the logo rather than a different drawing, which is how it stays
    recognisable as the same thing.
    """
    from fontTools.ttLib import TTFont  # noqa: F401  (fonts() needs it)

    serif, _ = fonts()
    size = SIZE
    x0, y0, x1, y1 = ink(draw(serif, BOTTOM, size))
    body_w, body_h = x1 - x0, y1 - y0
    side = body_w + 2 * (size * 0.26)
    d = draw(serif, BOTTOM, size, -x0, -y0)
    return (
        f'<path d="{rounded_rect(0, 0, side, side, side * 0.19)}" fill="{ground}"/>'
        f'<g transform="translate({(side - body_w) / 2:.2f} '
        f'{(side - body_h) / 2:.2f})"><path d="{d}" fill="{letters}"/></g>'
    ), side


CARD_W, CARD_H = 1200.0, 630.0
CARD_HEAD = ["Language technology for", "Ethiopia's 80+ languages"]
CARD_SUB = "Open datasets · models · evaluation · capacity building"
CARD_URL = "ethionlp.github.io"
CARD_TAGLINE = "NLP for Ethiopian languages"
INK, INK_3, RUST = "#16140f", "#736d62", "#9a3b2e"


def social_card() -> str:
    """The 1200x630 card link previews use.

    Baked to outlines like everything else here, for the same reason: the card
    is rendered by whoever is sharing the link, on a machine that has none of
    the site's fonts.
    """
    serif, ethiopic = fonts()
    body, body_semi = sans(400), sans(600)

    lock, lw, lh = lockup(GREEN, PAPER)
    scale = 108.0 / lh
    left, top = 80.0, 74.0

    parts = [
        f'<rect width="{CARD_W}" height="{CARD_H}" fill="{PAPER}"/>',
        # The same three-colour band the site puts at the top of the page.
        f'<rect width="{CARD_W / 3:.0f}" height="9" fill="{GREEN}"/>',
        f'<rect x="{CARD_W / 3:.0f}" width="{CARD_W / 3:.0f}" height="9" fill="{GOLD}"/>',
        f'<rect x="{CARD_W * 2 / 3:.0f}" width="{CARD_W / 3:.0f}" height="9" fill="{RUST}"/>',
        f'<rect y="{CARD_H - 9}" width="{CARD_W}" height="9" fill="{GREEN}"/>',
        f'<g transform="translate({left} {top}) scale({scale:.4f})">{lock}</g>',
    ]

    # The tagline sits beside the lockup, not under it: under it would make a
    # third line and the mark is already two.
    x = left + lw * scale + 30
    parts.append(f'<path d="{draw(body, CARD_TAGLINE, 27, x, top + 72)}" fill="{INK_3}"/>')

    for i, line in enumerate(CARD_HEAD):
        colour = GREEN if i else INK
        parts.append(f'<path d="{draw(serif, line, 70, left, 300 + i * 86)}" fill="{colour}"/>')

    parts.append(f'<path d="{draw(body, CARD_SUB, 30, left, 470)}" fill="{INK_3}"/>')
    parts.append(f'<path d="{draw(body_semi, CARD_URL, 27, left, 540)}" fill="{GOLD}"/>')

    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_W:.0f}" '
            f'height="{CARD_H:.0f}" viewBox="0 0 {CARD_W:.0f} {CARD_H:.0f}" role="img" '
            f'aria-label="EthioNLP: language technology for Ethiopia\'s 80+ languages">'
            f"\n  " + "\n  ".join(parts) + "\n</svg>\n")


HEADER = """{%- comment -%}
NOTE

Generated by scripts/build_logo.py, edit that, not this.
{%- endcomment -%}
"""


def header(note: str) -> str:
    """Liquid braces make str.format unusable here, so substitute by hand."""
    return HEADER.replace("NOTE", note)


def doc(body: str, w: float, h: float, cls: bool = False) -> str:
    attrs = ('class="{{ include.class }}" ' if cls
             else 'xmlns="http://www.w3.org/2000/svg" ')
    return (f'<svg {attrs}viewBox="0 0 {w:.1f} {h:.1f}" role="img" '
            f'aria-label="EthioNLP">\n  <title>EthioNLP</title>\n{body}\n</svg>\n')


def rasterise(sources: dict[str, Path], check: bool) -> None:
    """PNG icons, for the tab bar, iOS, and the manifest."""
    tool = shutil.which("rsvg-convert") or shutil.which("magick")
    if not tool:
        warn("rsvg-convert or magick not found; PNG icons left as they were")
        return
    jobs = [(IMG / n, sources[f], px, px, f) for n, px, f in RASTERS]
    jobs.append((IMG / "social-card.png", sources["card"], int(CARD_W), int(CARD_H), "card"))

    for dest, src, w, h, form in jobs:
        info(f"{dest.relative_to(ROOT)}  ({w}x{h}, {form})")
        if check:
            continue
        cmd = ([tool, "-w", str(w), "-h", str(h), str(src), "-o", str(dest)]
               if tool.endswith("rsvg-convert")
               else [tool, "-background", "none", "-density", "600",
                     str(src), "-resize", f"{w}x{h}", str(dest)])
        subprocess.run(cmd, check=True, capture_output=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="print, write nothing")
    args = parser.parse_args()

    try:
        themed, w, h = lockup("currentColor", None)
        flat, fw, fh = lockup(GREEN, PAPER)
        reversed_, rw, rh = lockup(PAPER, "#121110")
        badge_body, side = badge(GREEN, PAPER, GOLD)
        badge_rev, rside = badge(PAPER, GREEN, GOLD)
        tile_body, tside = tile(GREEN, PAPER)
        card = social_card()
    except ImportError:
        warn("fontTools is required:  pip install -r scripts/requirements.txt")
        return 1

    note = ("The wordmark: Ethio over NLP, the second line letter-spaced to the\n"
            "width of the first and cut out of the bar, so the page shows\n"
            "through it and the mark inverts for free on the dark theme.")

    lockup_html = header(note) + doc(themed, w, h, cls=True)
    badge_html = header("The compact mark: the wordmark inside a rounded square.") + doc(
        badge_body, side, side, cls=True
    )
    badge_svg, card_svg = VARIANTS / "badge.svg", VARIANTS / "social-card.svg"
    files = {
        card_svg: card,
        LOCKUP_INCLUDE: lockup_html,
        LOGO_INCLUDE: badge_html,
        # The browser draws the SVG favicon at tab size, so it gets the tile.
        FAVICON: doc(tile_body, tside, tside),
        VARIANTS / "wordmark.svg": doc(flat, fw, fh),
        VARIANTS / "wordmark-reversed.svg": doc(reversed_, rw, rh),
        badge_svg: doc(badge_body, side, side),
        VARIANTS / "badge-reversed.svg": doc(badge_rev, rside, rside),
    }

    step("Writing the logo")
    for path, content in files.items():
        info(f"{path.relative_to(ROOT)}  ({len(content)} bytes)")
        if not args.check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    step("Rendering the icons")
    rasterise({"tile": FAVICON, "badge": badge_svg, "card": card_svg}, check=args.check)
    if args.check:
        info("--check: nothing written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
