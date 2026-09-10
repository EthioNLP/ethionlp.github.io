# ethionlp.github.io

The EthioNLP community website. A Jekyll site whose content lives in plain text
files, and whose ecosystem data, models, datasets, repositories, publications
and the progress dashboard, is regenerated from public APIs rather than
maintained by hand.

**Contributing?** See **[CONTRIBUTING.md](CONTRIBUTING.md)**, it covers the
form-based ways in (most of which need no GitHub account) as well as working on
the code. This file is the maintainer's reference for how the machinery works.

---

## Running it locally

macOS ships Ruby 2.6, which is too old. Install a modern one once:

```sh
brew install ruby@3.4
```

Then, from the repository root:

```sh
make serve
```

That installs the gems into `vendor/bundle` on first run and serves the site at
<http://localhost:4000> with live reload. `make serve PORT=4123` uses a
different port. `make build` produces a one-off build in `_site/`, and
`make build-prod` reproduces the deployed output in `_site_prod/`.

`make clean` removes build output. Nothing in the Makefile touches git.

### Refreshing the data

```sh
make sync            # everything, in dependency order
make sync-hf         # just one source
make sync-pubs
make sync-github
make sync-progress
make sync-catalog    # the language catalogue
make sync-expertise  # who works on which language
```

`sync-expertise` reads the other four generated files, so it runs last.
`sync-catalog` must run after `sync-hf`: it joins the Hugging Face artifact
counts onto each language, and reads `_data/generated/huggingface.yml` to do so.
`make sync` already orders them correctly.

Each script writes into `_data/generated/` and prints what it found. Review the
result with `git diff _data/generated`. Only Python 3 and PyYAML are needed
(`make deps` installs them). This also runs nightly in CI, which opens a pull
request when anything changed.

---

## How the site is put together

| Path | What it is |
| --- | --- |
| `_members/*.md` | One file per community member. Front matter only; an optional Markdown body becomes their bio. |
| `_events/*.md` | One file per event. `_events/EXAMPLE-community-seminar.md` documents every field and is excluded from the build. |
| `_news/*.md` | One file per news item. |
| `_topics/*.md` | One file per open thesis or project topic, shown on `/mentorship/`. |
| `_data/*.yml` | Curated data: navigation, focus areas, channels, milestones, and the hand-written publication and ecosystem entries. |
| `_data/generated/*.yml` | **Machine-owned.** Overwritten by `make sync`, never edit these. |
| `_includes/`, `_layouts/` | Templates. `_includes/icon.html` holds the whole icon set. |
| `_sass/`, `assets/` | The design system, and two small dependency-free scripts. |
| `scripts/` | The sync and scaffolding tools. Standard library plus PyYAML. |
| `scripts/build_logo.py` | Regenerates the mark from Noto Sans Ethiopic. Needs `fonttools`; nothing else does. |
| `.github/` | Issue forms and the workflows that turn them into pull requests. `add-photo.yml` accepts a real file upload: `from_issue.py --kind photo` fetches the attachment off GitHub's CDN into `resources/img/gallery/`. |

### Curated versus generated

Generated files carry a banner saying so. If something in one of them is wrong,
fix it in the curated file that overrides it:

- a publication, `_data/publications_manual.yml`, matched on the title
- an extra repository, `_data/ecosystem_manual.yml`
- a person's details, their file in `_members/`
- a timeline entry, `_data/milestones.yml`

Curated values always win, so a correction survives the next sync.

---

## Common tasks

### Add a member

Either let the issue form do it, a "Join EthioNLP" issue opens a pull request
automatically, or scaffold the file yourself from any profile URL:

```sh
make member URL=https://github.com/someone
python3 scripts/new_member.py https://huggingface.co/someone https://orcid.org/0000-… \
        --name "Full Name" --focus data,models
```

Then fill in the identifiers so their publications sync:

```sh
python3 scripts/resolve_ids.py --check     # report what it would fill in
python3 scripts/resolve_ids.py             # write it into _members/
```

`resolve_ids.py` only accepts a match when the OpenAlex display name contains
both the first and last name *and* the author's topics are language-technology
topics. Ethiopian names are widely shared and a wrong id silently attributes
someone else's papers, so anything it is unsure about is reported and left for a
human.

### Add an event

Copy `_events/EXAMPLE-community-seminar.md`, rename it to
`_events/YYYY-MM-DD-your-slug.md`, delete the `published: false` line, and fill
in the fields. Only `title`, `kind` and `start` are required.

`status: open` marks a slot with no speaker yet, it shows on the events page
with a "claim this slot" button. `status: cancelled` keeps an event on the
record with a strike through it. Deleting the file removes it entirely.

The site publishes a subscribable calendar at `/events/calendar.ics`, built from
the same files.

### Add a news item

`_news/YYYY-MM-DD-slug.md` with `title` and `date`, optionally `kind`, `image`
and `link`. The body is Markdown.

---

## Deployment

The site is compatible with both GitHub Pages builders:

- **Classic Pages** builds it with Jekyll 3.9 straight from the branch. Nothing
  to configure.
- **GitHub Actions** (`.github/workflows/deploy.yml`) builds it with the Jekyll
  version in the `Gemfile` and also checks for internal links with no target.
  Enable under *Settings → Pages → Build and deployment → Source: GitHub Actions*.

Two other workflows run automatically:

- `sync-data.yml`, nightly data refresh, opens a pull request when anything
  changed.
- `from-issue.yml`, turns a completed "Join EthioNLP" or "Propose a talk" issue
  into a pull request adding the file.

---

## Conventions worth knowing

- **The design system is token-driven.** Every colour resolves through a custom
  property defined in `_sass/_tokens.scss`, twice: once for light and once for
  dark. Adding a hard-coded colour anywhere else will break dark mode.
- **Charts are inline SVG generated at build time** from `_data/generated/`. No
  chart library, no runtime fetch; the numbers are in the HTML.
- **Filtering is one implementation.** `assets/js/filter.js` binds any
  `[data-filter-root]` and works purely from `data-*` attributes, so a page can
  add a facet without touching JavaScript. Its markup contract is documented at
  the top of the file.
- **The progress dashboard states its method on the page.** If you change how it
  counts, change that text too.

## Licence

Content is CC BY 4.0. The site code is MIT, see `LICENCE`.

---

## Mentorship

`/mentorship/` is assembled from two places, so nothing is listed twice.

**Mentors** come from `_members/*.md`. A member becomes a mentor by adding four
keys to their own file:

```yaml
mentoring: [data, models]          # keys from _data/focus_areas.yml
mentoring_levels: [msc, phd]       # bsc | msc | phd | intern | career
mentoring_capacity: 2              # students they can take this cycle
mentoring_note: >-
  What they are happy to be asked about.
```

**Topics** are one file each in `_topics/`. Copy an existing one; the front
matter is `title`, `level`, `area`, `languages`, `mentor` (a member's slug),
`status`, `effort`, `prerequisites` and `posted`. Set `status: taken` to retire a
topic without deleting it; the description stays useful as a statement of the
gap.

The programme copy, the level vocabulary and the stated expectations live in
`_data/mentorship.yml`.

> The mentors currently listed were seeded to make the page render with real
> people. **Each of them should confirm their own areas, levels and capacity
> before this goes live.**

---

## The language catalogue

`/languages/` lists every language of Ethiopia with its family, script, speaker
count and what language technology exists for it.

The file is generated, so corrections belong upstream, in
[Glottolog](https://glottolog.org/) or [Wikidata](https://www.wikidata.org/), where they improve every project using those sources. `make sync-catalog` picks
them up on the next run.

Two things the script computes that the templates cannot: the map coordinates
(Liquid has no floating-point division, so a projection written in a template
collapses every point into one corner) and the join between a language and its
Hugging Face artifacts (the two sources spell several languages differently;
`ARTIFACT_ALIASES` in `scripts/sync_catalog.py` reconciles them, and the script
warns about any tag it could not place).

---

## Ways to contribute

Every way a visitor can add to the site lives in one place,
[`_data/contribute.yml`](_data/contribute.yml). Three surfaces read it: the
`/contribute/` page, the band above the footer on every page, and the footer's
Contribute column. Add one there and it appears in all three.

Each entry carries what it costs (`effort`) and what it needs (`account`:
`none`, `github` or `git`), because those are what people decide on, and a
`docs` anchor pointing at the section of [CONTRIBUTING.md](CONTRIBUTING.md) that
explains it in full. Set `featured: true` to put one in the band; keep that
to four, or the band stops being a call to action and becomes a menu.

A page can opt out of the band with `contribute_band: false` in its front
matter. Only `/contribute/` itself does, where it would be a smaller copy of the
page it sits on.

---

## The logo

The logo is the name on two lines: **Ethio** above, **NLP** below, letter-spaced
until it is exactly as wide as the word above it and cut out of a solid bar. The
cut is a real hole (one path, `fill-rule="evenodd"`), so the page shows through
the letters and the mark inverts for free on the dark theme.

There are three forms, and each exists because the one above it stops working at
that size:

| Form | Used for | Why |
| --- | --- | --- |
| Lockup | Header, wordmark exports | The full mark |
| Badge | Footer, home-screen icons | The same two lines, squared off |
| Tile | Favicon, 32px and below | Eight letters turn to mush that small, so it keeps `NLP` alone |

```sh
python3 scripts/build_logo.py          # write everything
python3 scripts/build_logo.py --check  # list what it would write
```

That writes `_includes/lockup.html` and `_includes/logo.html`, the favicon, the
PNG icon set, the social card, and the standalone SVGs under `assets/img/logo/`.
All type is baked to outlines, so nothing depends on a font having loaded, which
matters most off-site: a link preview, or someone's slide deck.

The fonts it extracts from are Source Serif 4, Source Sans 3 and Noto Sans
Ethiopic (all SIL OFL), downloaded on demand into the gitignored
`scripts/.cache/`. The PNGs need `rsvg-convert` or ImageMagick on `PATH`; without
one the SVGs are still written and the existing PNGs are left alone.

---

## Who is listed, and who is not

The site lists the people from the previous team page, and nobody else.

Everyone imported from the Hugging Face organisation is held at
`published: false` with `confirmed: false` in their `_members/` file. Jekyll
drops unpublished documents from the collection entirely, so there is no
profile, no listing, and no count, being in an organisation is not consent to
appearing on a public website.

Their models and datasets are still shown, in the *related* tier, because that
is about the work rather than about them.

```sh
make pending                                   # who is waiting, and how to ask
python3 scripts/pending_members.py --message   # the text to send
python3 scripts/pending_members.py --csv       # for a mail merge
```

There is no automated way: the Hub does not expose member email addresses, and
should not. Send the message through Telegram or the mailing list; people
confirm themselves through the "Confirm my listing" issue form, and a maintainer
then deletes the two lines.

---

## Three tiers of ownership

The distinction the ecosystem pages are built around:

| Tier | What it is | Where it shows |
| --- | --- | --- |
| `ethionlp` | The EthioNLP org, and teams registered in `_data/organisations.yml` | /ecosystem/ |
| `member` | A confirmed member's personal account | /ecosystem/ |
| `related` | Everything else, including orgs a member merely belongs to | /ecosystem/related/ |

The third tier exists because of a mistake worth not repeating. An earlier
version swept every organisation a member belonged to and called the results
"ours", which credited this community with `bigscience/mt0` and a multilingual
toxicity classifier on the strength of one member holding org membership.
**Belonging to an organisation is not authorship.** Only an explicit
registration in `_data/organisations.yml`, reviewed in a pull request, promotes
an organisation's work to `ethionlp`.

---

## Teams

A group, a lab, a project, a student club, registers its Hugging Face and
GitHub **organisations** rather than individual models. From then on everything
it publishes that covers an Ethiopian language is picked up by the nightly sync.

Registered teams live in `_data/organisations.yml`, and the "Register a team or
lab" issue form opens a pull request adding one. Nobody from the team has to be
listed in `_members/` first; that is the case this covers, and the reason it
exists alongside the automatic discovery below.

**Automatic discovery.** `sync_huggingface.py` also reads the public profile of
every *verified* member and sweeps the Hub organisations they belong to. This is
how `uhhlt/am-roberta`, the most-downloaded model built specifically for an
Ethiopian language, reaches the ecosystem page without being registered
anywhere.

"Verified" means a member with a Scholar, ORCID, OpenAlex or DBLP identifier.
The gate is not decorative: following *every* listed member's organisations
returned 1,758 of them, because the accounts imported from the Hugging Face
organisation include people who have joined hundreds of unrelated ones.

**Focused vs multilingual.** Both sweeps reach genuinely multilingual work, mt0 covers a hundred languages, of which Amharic is one. That is kept, but
labelled `breadth: multilingual`, listed in its own section, and excluded from
the headline totals and the language-coverage figures. A hundred-language model
is not the same claim as a model built for Amharic.

---

## Who works on which language

`scripts/sync_expertise.py` derives this rather than asking anyone to declare
it: Hugging Face language tags are taken as given, and for papers and
repositories the language is inferred by matching its name as a whole word in
the title, abstract, description and topics.

It shows up in two places, as chips on a member's profile, and as the "People"
column in the language catalogue, which is the column a student uses to find
someone to write to.

The inference is deliberately narrow, and absence means nothing was detected,
not that the person does not work on the language. A missing mapping is a much
smaller problem than a wrong one.

---

## Collecting news

The community is global and mostly not on GitHub, so news arrives by whichever
door suits the person. They all end in the same place: a draft in `_news/`, a
pull request, and a maintainer's eye.

| Route | Needs an account? | Ingest |
| --- | --- | --- |
| Telegram channel, start a message with `/news` | no | `from_submissions.py` (daily) |
| Shared web form (Google Forms or similar) | no | `from_submissions.py` (daily) |
| GitHub issue form | yes | `from_issue.py` (on the issue) |
| Email to the community address | no | by hand |

`/news/submit/` explains all four to the community.

### Setting up the two automatic ones

Both are optional, and the collector exits quietly when neither is configured.

**Web form.** Make a form with a headline, a description, and optional link,
date, kind and names. Publish its responses sheet to the web as CSV, then set
the `NEWS_FORM_CSV` Actions secret to that URL, and `news_form_url` in
`_config.yml` to the public form URL (that one turns on the button). Column
headings are matched loosely, so you do not have to name them exactly.

**Telegram.** Create a bot with @BotFather, add it to the channel, and set the
`TELEGRAM_BOT_TOKEN` secret. Only messages starting `/news` or `#news` are
picked up; a channel is a conversation, and drafting every message in it would
be unusable.

**Team registrations.** The same shape, for `/teams/`. Make a form asking for
the team name, its Hugging Face and GitHub organisations, a website, a kind and
a sentence of description; publish the responses sheet as CSV; set the
`TEAM_FORM_CSV` secret to that URL and `team_form_url` in `_config.yml` to the
public form URL. `scripts/from_team_form.py` appends each new response to
[`_data/organisations.yml`](_data/organisations.yml) **commented out**, with a
note saying what to check. Uncommenting three lines is the review step.

Column headings are matched loosely and in priority order, so "What kind?" and
"Describe the team" do not fight over the same answer. A response whose slug is
already registered is skipped.

Submissions already turned into drafts are recorded in
`_data/generated/news_seen.json` and `_data/generated/team_seen.json`, so a
daily run does not recreate yesterday's, and deleting a draft rejects it
permanently.

Nothing is ever published automatically: `write_news` in `scripts/lib/news.py`
stamps `published: false` on everything that did not come from a maintainer.

---

## News from events

`scripts/scan_events.py` runs weekly (`.github/workflows/scan-events.yml`) and
checks the events in `_data/watched_events.yml` for two kinds of evidence: a
public programme page naming someone listed here, and a synced publication whose
venue and year match the event. Everyone found at the same event is aggregated
into **one** draft item.

**Nothing is published automatically.** The workflow opens a pull request, and
every draft carries `published: false`, which Jekyll honours by leaving the file
out of the site entirely. Publishing means a person read it, checked it,
rewrote the body and deleted that line. The check is enforced by the file, not
by anyone remembering.

### LinkedIn

LinkedIn is not scanned, and an API key would not change that.

Two separate things get conflated here, so to be precise:

* **Our LinkedIn is a *group*** (`/groups/10060447/`). The Groups API lives under
  LinkedIn's Compliance programme, which is
  [restricted to approved partners](https://learn.microsoft.com/en-us/linkedin/compliance/integrations/groups/group-posts-and-actions), archiving vendors serving regulated industries. No key is available to a
  research community.
* **A key *is* obtainable for a Company Page**, through the
  [Community Management API](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/community-management-overview).
  It requires a legally registered entity, a verified Page, a super-admin of
  that Page to verify the app, and a two-tier review with a screen recording.

But even with that key approved; it would not do the job. **LinkedIn has no
keyword search API.** The nearest thing, People Typeahead, searches only your
own Page's followers, by the first characters of a name, ten results at a time.
There is no product that answers "who from our community was mentioned at the
Indaba", which is the only reason we wanted it.

What a Company Page key *would* allow is posting **to** our own page and reading
our own page's analytics. That is a fine thing to want later; it is an outbound
announcement feature, not a discovery one, and it is not what the scanner needs.

So the workaround stands: the "Share community news" issue form. A person
reading a post and writing two sentences beats a scraper that silently breaks, and unlike scraping; it does not violate LinkedIn's terms.

---

## Secrets and API keys

**Never commit a key to this repository.** That is the ordinary rule for any
repo, and there is a second reason here: this is a *public static site*, and
`_data/*.yml` is compiled into the published output. A key placed there would be
leaked twice over, visible in the Git history and served from the site itself.

The pattern the scripts already use is an environment variable, read at run time
and never written to disk:

```python
token = os.environ.get("GITHUB_TOKEN")
```

**In CI**, put the value in *Settings → Secrets and variables → Actions* and pass
it into the step, as `sync-data.yml` already does:

```yaml
env:
  GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

**Locally**, export it in your shell or keep it in a gitignored `.env` that you
source by hand. `.env` is already covered by `.gitignore`. Do not add a
`python-dotenv` dependency for this, the sync scripts deliberately need only
PyYAML.

If a key is ever committed by accident, rotate it. Deleting the commit is not
enough: it is already in the clone anyone made, and in GitHub's cache.

One further reason LinkedIn is a poor fit for a scheduled job: its OAuth access
tokens expire after about 60 days and must be refreshed interactively. A weekly
cron would break every couple of months and need a human to re-authorise it.
