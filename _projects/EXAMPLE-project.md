---
# ── TEMPLATE ─────────────────────────────────────────────────────────────────
# `published: false` keeps this file out of the site. Copy it, give the copy a
# real name, delete this comment and the published line, and fill in the rest.
#
#   cp _projects/EXAMPLE-project.md _projects/my-project.md
#
# The filename becomes the URL: _projects/walia-llm.md -> /projects/walia-llm/
published: false

# Required.
title: A short name for the project
summary: >-
  One or two sentences a person outside the community would understand. What
  the work is and why it exists, not how it is built.

# active | shipped | paused. Shown as the label above the title.
status: active

# Member slugs, i.e. the filename of the file in _members/ without .md.
# They are rendered in the community's canonical order, not the order here.
people:
  - seid-muhie-yimam

# Language names as the catalogue spells them (see _data/generated/catalog.yml).
languages:
  - Amharic

# Whatever the project produced. Every one of these is optional; omit the line
# rather than leaving it blank.
paper:
model:
dataset:
code:
---

The body is Markdown and carries the detail. A structure that works:

**What the problem is.** The gap this project exists to close, in plain terms.

**What has been done.** Where the work has got to, and what is usable today.

**What is next.** What would help, and what someone joining could pick up.
