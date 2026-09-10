#!/usr/bin/env python3
"""List the people who are known but not published, and draft the ask.

Membership of the EthioNLP organisation on Hugging Face is not consent to being
listed on a public website. Everyone imported from that organisation is held at
`published: false` until they say yes, and this script is how you ask them.

    python3 scripts/pending_members.py              # who is waiting
    python3 scripts/pending_members.py --message    # text to send
    python3 scripts/pending_members.py --csv        # handles, for a mail merge

There is no automated route: Hugging Face does not expose member email
addresses, and it should not. Send the message through the channel these people
already use, the Telegram group, the mailing list, or a direct message on the
Hub, and let them come to the form themselves.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.common import info, read_members, step  # noqa: E402

SITE = "https://ethionlp.github.io"
REPO = "EthioNLP/ethionlp.github.io"
FORM = f"https://github.com/{REPO}/issues/new?template=confirm-listing.yml"

MESSAGE = f"""\
Subject: Would you like to be listed on the EthioNLP site?

Hello,

We have rebuilt the EthioNLP website ({SITE}). It now keeps itself current: it
pulls models and datasets from Hugging Face, publications from OpenAlex and the
ACL Anthology, and code from GitHub, so a profile stays up to date without
anyone editing it.

You are a member of the EthioNLP organisation on Hugging Face, which is how we
know of your work. We have **not** published a profile for you, because being in
an organisation is not the same as agreeing to appear on a public website.

If you would like to be listed, fill this in; it takes a minute:

    {FORM}

If you would rather not, just ignore this. Nothing is published and we will not
ask again.

Either way, your Ethiopian-language models and datasets are already shown on the
site as work, under "work by the wider community". That is about the work rather
than about you, and we can remove it on request.

Thank you,
EthioNLP
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--message", action="store_true", help="print the text to send")
    parser.add_argument("--csv", action="store_true", help="print name,huggingface")
    args = parser.parse_args()

    members = read_members()
    pending = [m for m in members if m.get("confirmed") is False]
    listed = [m for m in members if m.get("confirmed") is not False]

    if args.csv:
        print("name,huggingface,profile")
        for m in sorted(pending, key=lambda m: m["slug"]):
            handle = m.get("huggingface") or ""
            url = f"https://huggingface.co/{handle}" if handle else ""
            print(f'"{m.get("name", "")}",{handle},{url}')
        return 0

    if args.message:
        print(MESSAGE)
        return 0

    step(f"{len(listed)} listed, {len(pending)} awaiting confirmation")
    for m in sorted(pending, key=lambda m: m["slug"]):
        handle = m.get("huggingface") or ""
        info(f"{(m.get('name') or m['slug']):<32} {handle}")

    if pending:
        step("How to ask")
        info("python3 scripts/pending_members.py --message   # the text")
        info("python3 scripts/pending_members.py --csv       # for a mail merge")
        info("Send it via Telegram, the mailing list, or a Hub DM.")
        info(f"They confirm here: {FORM}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
