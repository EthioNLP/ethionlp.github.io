---
title: A documentation-to-dataset pipeline for Omotic languages
level: phd
area: data
languages: [Wolaytta, Gamo, Kafa]
mentor: seid-muhie-yimam
status: open
effort: 3–4 years
prerequisites:
  - Background in either computational linguistics or language documentation
  - Willingness to do fieldwork-adjacent collaboration
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

The Omotic languages are the least-resourced branch in Ethiopia and among the
least-resourced anywhere. There is descriptive linguistic work, grammars,
wordlists, recordings held by universities and by SIL, but almost none of it is
in a form any NLP system can read.

**The gap.** The bottleneck is not model architecture. It is that decades of
existing documentation sit in PDFs, ELAN files and filing cabinets, in
inconsistent orthographies, with unclear rights.

**What you would do.** Build the pipeline that turns that material into usable
data: OCR and layout analysis for printed grammars, orthography normalisation,
alignment of recordings to transcripts, and, the hard part, a rights and
consent framework that the communities involved actually agree to.

**What finished looks like.** Released corpora for at least three Omotic
languages, a reusable pipeline, and a written account of the consent process
that other documentation projects can adopt. This is as much a data-governance
thesis as an engineering one.
