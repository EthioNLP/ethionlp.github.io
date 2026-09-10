---
title: Low-footprint speech recognition for Tigrinya
level: msc
area: applications
languages: [Tigrinya]
mentor: abinew-ali-ayele
status: open
institutions: [Bahir Dar University]
effort: 6–12 months
prerequisites:
  - PyTorch, and some prior contact with speech or audio
  - Access to a GPU for at least part of the project
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

Tigrinya has perhaps a hundred hours of transcribed speech in the open, against
the tens of thousands behind English ASR. The interesting question is not
whether a large multilingual model can be fine-tuned onto it; it can, but
whether the result can run somewhere a speaker would actually meet it.

**The gap.** Published Tigrinya ASR results all assume a server. Nothing has
been reported for a model small enough to run offline on a mid-range Android
phone, which is the only deployment that matters for most of the speaker
population.

**What you would do.** Fine-tune a self-supervised speech model on the available
Tigrinya data, then take compression seriously: distillation, quantisation,
pruning. Report word error rate against on-device latency and memory, not just
word error rate.

**What finished looks like.** A curve, not a number, WER against model size, and a working demonstration on real hardware.
