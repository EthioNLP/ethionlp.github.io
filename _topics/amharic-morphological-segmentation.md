---
title: Morphological segmentation for Amharic user-generated text
level: msc
area: linguistics
languages: [Amharic]
mentor: seid-muhie-yimam
status: open
institutions: [Addis Ababa University, Universität Hamburg]
effort: 6–9 months
prerequisites:
  - Python, and comfort reading a linguistics paper
  - Reading knowledge of Amharic (essential; the error analysis is the thesis)
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

Amharic is templatic and heavily affixed: a single orthographic word can carry
a verb root, subject and object markers, tense, negation and a preposition.
Every downstream model in this ecosystem currently either ignores that or hands
it to a subword tokenizer trained on running text, which splits at points no
speaker would recognise.

**The gap.** There are morphological analysers for Amharic, but they were built
against clean, edited text. On social media, transliterated input and OCR output
they fall over, and nobody has measured by how much.

**What you would do.** Build a segmentation evaluation set from genuinely messy
Amharic, a few thousand words, hand-segmented, drawn from at least three
registers. Measure the existing analysers against it. Then train a neural
segmenter and report where it wins and where it does not.

**What finished looks like.** A public evaluation set, a table of results for at
least three systems, and an error analysis that names the linguistic phenomena
each one fails on. The error analysis is the contribution; the model is the
supporting evidence.
