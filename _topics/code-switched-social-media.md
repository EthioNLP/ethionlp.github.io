---
title: Amharic–English code-switching in Ethiopian social media
level: msc
area: linguistics
languages: [Amharic]
mentor: abinew-ali-ayele
status: open
effort: 6–9 months
prerequisites:
  - Reading knowledge of Amharic
  - Basic Python; annotation experience helps
posted: 2026-02-01
# ── NOT PUBLISHED ────────────────────────────────────────────────────────────
# Drafted as seed content when the site was rebuilt, and not yet confirmed with
# the person named as mentor. Nobody should be advertised as supervising a
# thesis without being asked, so this stays out of the build.
#
# To publish it: confirm with the mentor, then delete this comment and the
# `published: false` line.
published: false
---

Ethiopian social media is not written in Amharic. It is written in Amharic,
English, Latin-script transliterated Amharic and combinations of all three,
often inside a single sentence. Every model in this ecosystem is trained as if
that were not the case.

**The gap.** No annotated Ethiopian code-switching corpus has been publicly
released, so the cost of ignoring it has never been quantified. One was
announced at the 2025 EthioNLP workshop; check whether it is out before you
start.

**What you would do.** Build a token-level language-identification corpus from
public posts, following the consent and anonymisation practice this community
already uses for hate-speech data. Measure how much accuracy existing Amharic
classifiers lose on code-switched input versus monolingual input.

**What finished looks like.** A released corpus, a language-identification
baseline, and a number for the accuracy gap, which is the number that would
justify anyone doing something about it.
