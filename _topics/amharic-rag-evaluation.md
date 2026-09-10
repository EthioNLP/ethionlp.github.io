---
title: Retrieval-augmented question answering in Amharic
level: bsc
area: applications
languages: [Amharic]
mentor: henok-biadglign-ademtew
status: open
effort: One semester
prerequisites:
  - Python
  - No prior NLP required
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

Retrieval-augmented generation is the standard way to make a language model
answer questions about a specific body of documents. In Amharic almost nobody
has checked whether the retrieval half works at all, Ethiopic script,
inconsistent spelling and rich morphology all break the usual assumptions.

**The gap.** Demos exist. Measurements do not.

**What you would do.** Assemble a small Amharic document collection with a
public licence, health information, agricultural extension material, or
university regulations. Write a few hundred questions with answers grounded in
it. Compare retrieval methods: keyword search, multilingual dense retrieval,
and one with morphological normalisation in front of it.

**What finished looks like.** A comparison table and a set of questions that
every method gets wrong, with an explanation of why. Scoped to one semester
deliberately; this is a good first research project.
