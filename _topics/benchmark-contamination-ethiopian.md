---
title: Benchmark contamination in Ethiopian-language evaluation
level: msc
area: evaluation
languages: [Amharic, Tigrinya, Afaan Oromo]
mentor: israel-abebe-azime
status: open
effort: 4–6 months
prerequisites:
  - Comfort with the Hugging Face stack
  - Patience for careful, unglamorous measurement
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

Every benchmark this community has published is on the open web, which means it
is plausibly inside the pretraining data of the models being evaluated on it. If
that is true, some of the reported progress in Ethiopian-language NLP is not
progress.

**The gap.** Contamination has been studied at length for English. For African
languages it has barely been looked at, and the standard detection methods
assume access to pretraining corpora that nobody has.

**What you would do.** Apply the existing contamination probes, membership
inference, canary strings, n-gram overlap against open corpora, to the main
Ethiopian-language benchmarks and the models commonly evaluated on them. Then
build a small, genuinely held-out replacement set for whichever benchmark turns
out to be worst affected.

**What finished looks like.** An honest answer, including the answer "we cannot
tell, and here is why". A negative result is publishable here and would change
how this community reports numbers.
