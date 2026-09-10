---
# ─────────────────────────────────────────────────────────────────────────────
# TEMPLATE, copy this file, rename it, and delete the `published: false` line.
#
# `published: false` keeps a file out of the built site entirely, so this one
# never appears anywhere. It exists to document every field an event can have.
# Only `title`, `kind` and `start` are required; everything else is optional.
#
# Use `draft: true` instead if you want to park a real event temporarily, it
# has the same effect on the listings but is easier to spot in a diff.
#
# Filename convention:  _events/YYYY-MM-DD-short-slug.md
# The date in the filename is only for tidy sorting in the folder, the site
# reads the `start:` field below.
# ─────────────────────────────────────────────────────────────────────────────
published: false

title: Amharic morphology in the age of subword tokenisers
kind: seminar            # seminar | workshop | conference | tutorial | hackathon | reading-group
start: 2026-03-12        # required, YYYY-MM-DD
end:                     # optional; leave empty for a single-day event
time: "17:00"            # optional, 24-hour, local to `timezone`
duration: 60             # optional, minutes, used for the calendar entry
timezone: EAT            # EAT (Addis Ababa) unless stated otherwise

location: Online
online: true
join_url: https://meet.example.org/ethionlp
venue_url:               # a page about the physical venue, if there is one
colocated_with:          # e.g. "ACL 2026", if the event sits inside a larger one

# confirmed → a scheduled event
# open      → a slot with no speaker yet; shown on the events page as claimable
# cancelled → kept for the record, struck through
status: confirmed

featured: false          # pin to the top of the events page and show on the home page
focus: [linguistics, models]   # any of: data, models, applications, evaluation, capacity, linguistics

summary: >-
  One paragraph, plain language, no more than about forty words. This is what
  shows on the events list and in search results.

speakers:
  - name: Full Name
    affiliation: University of Somewhere
    member: seid-muhie-yimam   # optional: a slug from _members/, which links the profile
    url: https://example.org

organisers:
  - name: Full Name
    affiliation: Somewhere

register: https://example.org/register    # a registration or RSVP link
recording: https://youtu.be/xxxxxxxx      # added after the event
slides: /assets/files/example-slides.pdf

# Calls for contributions, for workshops and conferences.
cfp:
  submit: https://example.org/submit
  abstract_deadline: 2026-01-31
  paper_deadline: 2026-02-28
  notification: 2026-02-14
  formats:
    - Extended abstracts (up to 2 pages)
    - Full papers (4–8 pages)

# Accepted contributions, added once the programme is set. Each entry takes
# `title`, `authors` and an optional `abstract`, `url` and `slides`.
papers: []
---

Everything below the front matter is the event page body, written in Markdown.
Use it for the full description, the schedule, travel notes, whatever a reader
needs. Headings, lists, links and tables all work.

## Schedule

| Time  | Item                    |
| ----- | ----------------------- |
| 17:00 | Talk                    |
| 17:40 | Questions and discussion |
