# Contributing to the EthioNLP site

This site belongs to the community, and almost everything on it was put there by
someone who is not a maintainer. You do not need to be a web developer, and for
most things you do not need a GitHub account either.

**[→ The same list as a web page](https://ethionlp.github.io/contribute/)**, if
you would rather not read a long document: every way in, what each one costs, and
what happens after you submit. That page is built from
[`_data/contribute.yml`](_data/contribute.yml), and each of its entries links
back to the section here that explains it in full. **If you add or remove a way
in, change both**: the list lives in that file, the detail lives here.

**Find what you want to do, and skip the rest.**

| I want to… | Go to |
| --- | --- |
| Be listed as a member | [Add yourself](#add-yourself) |
| Add my lab or project | [Register a team](#register-a-team) |
| Share something that happened | [Share news](#share-news) |
| Announce a talk, workshop or seminar | [Add an event](#add-an-event) |
| Add a photograph | [Add to the gallery](#add-to-the-gallery) |
| Offer to supervise students | [Become a mentor](#become-a-mentor) |
| Post a thesis topic | [Post a topic](#post-a-thesis-topic) |
| Add a paper, model or dataset the site missed | [Add a resource](#add-a-resource) |
| Fix a mistake in the text | [Fix something](#fix-something) |
| Change how the site works | [Work on the code](#work-on-the-code) |

---

## Two ways to contribute

**Through a form.** Every common contribution has a form. You fill it in, a
robot turns it into a proposed change, and a maintainer merges it. You never see
any code. Most forms are GitHub issue forms, which need a free GitHub account, except news, which can be sent without an account at all.

**Through a pull request.** If you are comfortable with Git, edit the files
directly. This is faster for anything the forms do not cover, and it is the only
way to change the code. See [Work on the code](#work-on-the-code).

Either way, **nothing you submit goes live until a maintainer has read it.**
That is not distrust; it is so that nobody has to worry about breaking the
site.

---

## Add yourself

**[→ Open the "Join EthioNLP" form](https://github.com/EthioNLP/ethionlp.github.io/issues/new?template=join-community.yml)**

Give your name and any public profile links you have: a personal site, GitHub,
Hugging Face, Google Scholar, ORCID. One link is enough to start.

The point of asking for those is that **you never have to update your profile
again.** The site reads your publications from OpenAlex, Semantic Scholar, DBLP
and the ACL Anthology, your models and datasets from Hugging Face, and your
repositories from GitHub. Publish something anywhere, and it appears here within
a day.

A Google Scholar or ORCID identifier is the single most useful thing you can
give, because it is what makes the publication list work.

### Editing your own profile

Your page at `/community/your-name/` is built from one file,
`_members/your-name.md`, and the page itself has an **Edit this profile** button
that opens it. There is no login on this site: it is served as static files, so
any password it could check would be readable by everyone. GitHub does that job
instead, and a maintainer merges the change.

What you can set:

| Field | What it does |
| --- | --- |
| `name`, `role`, `affiliation`, `location` | the heading of your page |
| `photo` | a path under `resources/img/`; leave it out for initials |
| `website`, `github`, `huggingface`, `twitter`, `linkedin` | the icon row |
| `scholar`, `orcid`, `openalex`, `semantic_scholar`, `dblp` | what the publication sync follows |
| `focus` | your research areas. **Leave it empty** and the site works them out from your own papers and releases; fill it in and yours wins |
| `mentoring`, `mentoring_levels`, `mentoring_capacity`, `mentoring_note` | puts you on `/mentorship/` |
| `published` | set `false` to take your page off the site |

Your publications, models, datasets and repositories are **not** in the file.
They are synced from the identifiers above, so the way to correct them is to fix
the identifier.

### Were you invited to confirm a listing?

If someone sent you a link asking you to confirm, use the
**[Confirm my listing](https://github.com/EthioNLP/ethionlp.github.io/issues/new?template=confirm-listing.yml)**
form instead. You are in the EthioNLP organisation on Hugging Face, so we know
of your work, but being in an organisation is not the same as agreeing to
appear on a public website, so nothing has been published.

If you would rather not be listed, ignore it. Nothing happens and you will not
be asked again.

---

## Register a team

**[→ Open the "Register a team or lab" form](https://github.com/EthioNLP/ethionlp.github.io/issues/new?template=register-team.yml)**

For a research lab, a project, a student group or a company team.

A team registers its Hugging Face and GitHub **organisations**, not individual
models. From then on, everything the team publishes that covers an Ethiopian
language appears on the site by itself. Nothing outside those languages is
touched.

**Nobody from your team needs to be listed here first.** This is the form for a
group that has just started.

Registering is also what makes your group's work count as EthioNLP's own rather
than as related work; it is a human decision, reviewed in a pull request,
rather than something guessed from who belongs to which organisation.

---

## Share news

A defence, a paper accepted, a workshop run, an award, a dataset released, a
mention on the radio. **Two sentences and a link is enough**; somebody will
tidy the wording.

Four ways, and only the third needs an account:

1. **Telegram.** Post in the channel starting with `/news`. The first line
   becomes the headline, the rest the description, and any link is kept.
2. **The web form.** No login, works on a phone, under a minute.
3. **Email.** [ethionlp@googlegroups.com](mailto:ethionlp@googlegroups.com).
   A sentence in the body is fine.
4. **[The GitHub form](https://github.com/EthioNLP/ethionlp.github.io/issues/new?template=share-news.yml).**
   Structured fields, and the best one if you want to attach a photograph.

**[→ See all four, with links](https://ethionlp.github.io/news/submit/)**

A LinkedIn post is a perfectly good link. Paste the URL and the item will link
to it.

You do not need to submit conference participation: a weekly scan already checks
the major venues for papers by people listed here and drafts an item for each
event. It only catches things that leave a public trace, which is why this
section exists.

---

## Add an event

**[→ Open the "Propose a talk or event" form](https://github.com/EthioNLP/ethionlp.github.io/issues/new?template=propose-talk.yml)**

Seminars, workshops, tutorials, hackathons, reading groups. Give a title, a
date, and a couple of sentences.

Speakers especially welcome. A thesis chapter; a dataset you are annotating, or
a model that is not working yet are all good seminar topics; the audience is
people working on the same problems, not a conference committee.

---

## Add to the gallery

Photographs from workshops, conferences and gatherings.

**[→ Open the "Add a photograph" form](https://github.com/EthioNLP/ethionlp.github.io/issues/new?template=add-photo.yml)**

Drag the file into the form. GitHub takes the upload, and a workflow copies the
image into `resources/img/gallery/`, appends the entry to
[`_data/gallery.yml`](_data/gallery.yml) and opens a pull request. The image is
copied into the repository rather than linked, so the gallery does not break if
the original is deleted.

By hand instead: put the image in `resources/img/gallery/` and add the entry
yourself. Only `src` and `caption` are required; the file documents the rest.
Use plain ASCII filenames.

No GitHub account? Mail the photographs to
[ethionlp@googlegroups.com](mailto:ethionlp@googlegroups.com) with a sentence
about each.

Two things we ask. Write a caption that says what is happening rather than just
where it was. And only name people who are happy to be named; leave the
`people` field out if you are not sure.

---

## Become a mentor

Mentors are not required to be senior. If you have finished a thesis in this
area, you know more than the person starting one, and a second-year PhD student
is often a better first mentor than a professor.

Add four keys to your own file in [`_members/`](_members/):

```yaml
mentoring: [data, models]          # keys from _data/focus_areas.yml
mentoring_levels: [msc, phd]       # bsc | msc | phd | intern | career
mentoring_capacity: 2              # students you can take this cycle
mentoring_note: >-
  What you are happy to be asked about.
```

Capacity is shown publicly, so nobody is asked for more than they offered.

---

## Post a thesis topic

Add a file to [`_topics/`](_topics/). Copy an existing one; the front matter is
`title`, `level`, `area`, `languages`, `mentor`, `status`, `effort`,
`prerequisites` and `posted`.

A good topic says three things: what the gap is, what a student would actually
do, and what a finished result looks like. Look at the existing ones; they are
written to be read by someone deciding whether to spend a year on it.

Set `status: taken` to retire a topic rather than deleting it; the description
usually stays useful as a statement of the gap.

---

## Add a research project

**[→ Start a project file](https://github.com/EthioNLP/ethionlp.github.io/new/master/_projects?filename=_projects/my-project.md)**

A project is the unit between a research area and a single artifact: a named
effort with people on it that produced some combination of a paper, a model, a
dataset and code. A single paper is not a project; the line of work that
produced it is.

Copy [`_projects/EXAMPLE-project.md`](_projects/EXAMPLE-project.md), which
documents every field, and delete its `published: false` line:

```sh
cp _projects/EXAMPLE-project.md _projects/my-project.md
```

The filename becomes the URL, so `_projects/walia-llm.md` is published at
`/projects/walia-llm/` and appears on [/projects/](https://ethionlp.github.io/projects/).

Front matter is `title`, `summary`, `status` (`active`, `shipped` or `paused`),
`people`, `languages`, and any of `paper`, `model`, `dataset`, `code`. Two
fields are worth getting right:

- **`people`** takes member *slugs* — the filename in `_members/` without the
  `.md`. They render in the community's canonical order, not the order you list
  them in, so you do not need to rank anyone.
- **`languages`** takes language names as the catalogue spells them, which is
  the `name` field in `_data/generated/catalog.yml`. The catalogue says Oromo,
  Geez and Sidamo where you may be used to writing Afaan Oromo, Ge'ez and
  Sidama.

Set `status: paused` rather than deleting a project that has stopped; a
dormant project with a clear write-up is still the best answer to "has anyone
tried this?".

---

## Add a resource

**[→ Open the "Add a dataset, model or paper" form](https://github.com/EthioNLP/ethionlp.github.io/issues/new?template=add-resource.yml)**

Most models, datasets, repositories and papers arrive automatically. Use this
form when something has been missed, usually because it has no Ethiopian
language tag, or because the author is not listed here.

If it is *your* work and it is missing; the better fix is usually to
[add yourself](#add-yourself) or [register your team](#register-a-team), which
catches everything else you publish too.

---

## Fix something

Wrong affiliation, dead link, typo, clumsy sentence, a figure that looks wrong.

**The fastest way:** every page has an "Edit this page" link above the footer
that opens the right file in GitHub's editor. Change it, describe what you
changed, and submit. GitHub handles the fork and the branch for you.

**If the error is in generated data**, anything under `_data/generated/`, do
not edit the file, because the next sync overwrites it. Instead:

- a wrong publication → add a correction to `_data/publications_manual.yml`;
- a wrong language fact → fix it in [Glottolog](https://glottolog.org/) or
  [Wikidata](https://www.wikidata.org/), which improves every project using
  those sources, not just this site;
- anything else → [open an issue](https://github.com/EthioNLP/ethionlp.github.io/issues/new)
  and say what is wrong.

---

## Work on the code

For changes to layouts, styles, scripts or structure.

### Getting it running

You need Ruby 3.x. macOS ships Ruby 2.6, which is too old:

```sh
brew install ruby@3.4          # macOS
sudo apt install ruby-full     # Debian/Ubuntu
```

Then:

```sh
git clone https://github.com/EthioNLP/ethionlp.github.io.git
cd ethionlp.github.io
make serve
```

That installs the gems into `vendor/bundle` on first run and serves the site at
<http://localhost:4000> with live reload. `make serve PORT=4123` uses a
different port if that one is busy.

If `make serve` cannot find Ruby, it tells you where it looked. Everything else
is in the [Makefile](Makefile), which is short and commented.

### Contributing a change

```sh
git checkout -b short-description-of-change
# edit, and check it in the browser
make build                     # must pass with no Liquid errors
git commit -am "what changed and why"
git push -u origin short-description-of-change
```

Then open a pull request. If it changes anything visual, a screenshot in the
description saves a great deal of back and forth.

### How the site is put together

| Path | What it is |
| --- | --- |
| `_members/`, `_events/`, `_news/`, `_topics/` | One file per person, event, news item, thesis topic |
| `_data/*.yml` | Curated data: navigation, focus areas, teams, gallery |
| `_data/generated/*.yml` | **Machine-owned.** Overwritten by `make sync`, never edit |
| `_layouts/`, `_includes/` | Templates. `_includes/icon.html` holds the whole icon set |
| `_sass/`, `assets/` | The design system, and two small dependency-free scripts |
| `scripts/` | The sync and scaffolding tools. Standard library plus PyYAML |
| `.github/` | Issue forms, and the workflows that turn them into pull requests |

### Refreshing the data

```sh
make sync            # everything, in dependency order
make sync-hf         # or just one source
```

Only Python 3 and PyYAML are needed (`make deps` installs them). Review the
result with `git diff _data/generated`. This also runs nightly in CI, which
opens a pull request when anything changed.

### House style

Not rules so much as what the existing code does, so that the next person can
read it:

- **Comments say why, not what.** The code already says what. Several comments
  in `scripts/` exist because someone got it wrong the first time and wrote down
  the reason, those are the valuable ones.
- **No new dependencies without a reason.** The sync scripts use the standard
  library plus PyYAML, which is why the CI job needs no lockfile and runs in
  seconds. The site itself ships no JavaScript framework.
- **Templates must survive missing data.** Every generated file can be absent or
  empty; a page that renders a blank section is fine, a page that crashes is
  not.
- **Liquid cannot do floating-point arithmetic**, and a name-based join in a
  template silently drops anything spelled differently by the two sources.
  Compute both in Python and let the template do lookups.
- **Do not overstate what this community built.** Work by EthioNLP is kept apart
  from Ethiopian-language work by others, and work built *for* a language apart
  from multilingual work that merely lists one. Both distinctions are enforced
  in `scripts/sync_huggingface.py`; please keep them.
- **Nobody is published without consent.** People are listed only after
  confirming. Please do not add a way around that.

### Accessibility and performance

The site is meant to be usable on a slow connection and a cheap phone, which is
what much of its audience has.

- It works with JavaScript disabled. Charts are server-rendered SVG; filters and
  the theme toggle are progressive enhancements.
- Images need `loading="lazy"` and real `alt` text.
- Light and dark themes both need checking, `data-theme="dark"` on `<html>`.
- Keyboard navigation must work. The header menus open on hover *and* on click
  for exactly this reason.

---

## Getting help

- **[Open an issue](https://github.com/EthioNLP/ethionlp.github.io/issues/new)**, anything at all, including "how do I…".
- **[ethionlp@googlegroups.com](mailto:ethionlp@googlegroups.com)**, if you would rather not use GitHub.
- **Telegram**, the fastest way to reach someone.

A half-finished pull request with a question in the description is welcome. So
is an issue that only says something looks wrong without knowing why.

## Licence

Content is [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); the code
is under the repository's licence. By contributing you agree your contribution
is published on those terms.
