"""Tests for scripts/review_join_pr.py.

    python3 -m unittest discover -s tests
"""

from __future__ import annotations

import base64
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from review_join_pr import (  # noqa: E402
    MARKER,
    ChangedFile,
    GitHub,
    is_join_issue,
    orcid_checksum_ok,
    render,
    review,
    review_pull_request,
    upsert_comment,
)

CONSENT = """### Confirmation

- [x] I am happy for this information to appear on a public website, and I understand it lives in a public Git repository that I can edit or remove at any time.
- [x] I have read the community standards at https://ethionlp.github.io/standards/ and agree to them, including the rules for posting in the Telegram and Discord groups.
"""

FORM = """### Full name

Khalil Etana

### Role

Industrial Engineering Undergraduate Student

### Affiliation

Wollega University, Shambu Campus

### Where you are based

Shambu, Ethiopia

### GitHub

https://github.com/khaliletanamoh

### Hugging Face

_No response_

### Google Scholar

https://scholar.google.com/citations?user=YTWf6A0AAAAJ&hl=en

### ORCID

https://orcid.org/0009-0005-5740-7324

### Personal site

https://khaliletanamoh.com

### LinkedIn

https://www.linkedin.com/in/khaliletanamohd

### Research tracks

- [ ] Datasets & corpora
- [x] Language models
- [ ] Applications
- [ ] Evaluation & benchmarks
- [x] Capacity building
- [x] Language & linguistics

### A sentence or two about your work

I study NLP for Ethiopian languages.

### Which describes you?

Student member (bachelor): joining the students chapter

""" + CONSENT

PROFILE = """---
name: Khalil Etana
title: Khalil Etana
role: Industrial Engineering Undergraduate Student
affiliation: Wollega University, Shambu Campus
location: Shambu, Ethiopia
order: 900
focus: [models, capacity, linguistics]
website: "https://khaliletanamoh.com"
github: khaliletanamoh
huggingface:
scholar: "https://scholar.google.com/citations?user=YTWf6A0AAAAJ&hl=en"
orcid: 0009-0005-5740-7324
semantic_scholar:
dblp:
linkedin: "https://www.linkedin.com/in/khaliletanamohd"
membership: bachelor
---

I study NLP for Ethiopian languages.
"""

MINIMAL_FORM = """### Full name

Almaz Tesfaye

### Role

_No response_

### Affiliation

_No response_

### Where you are based

_No response_

### GitHub

_No response_

### Hugging Face

_No response_

### Google Scholar

_No response_

### ORCID

_No response_

### Personal site

_No response_

### LinkedIn

_No response_

### Research tracks

- [ ] Datasets & corpora
- [ ] Language models

### A sentence or two about your work

_No response_

### Which describes you?

Member: Ethiopian, or working extensively on Ethiopian languages

""" + CONSENT

MINIMAL_PROFILE = """---
name: Almaz Tesfaye
title: Almaz Tesfaye
order: 900
huggingface:
scholar:
orcid:
semantic_scholar:
dblp:
---
"""

FILES = [ChangedFile("_members/khalil-etana.md")]
WITH_OPENALEX = PROFILE.replace("membership: bachelor", "membership: bachelor\nopenalex: A123")


def run(form=FORM, profile=PROFILE, files=None, author="khaliletanamoh", openalex=None):
    return review(form, files or FILES, profile, author, openalex)


class ReadySubmissions(unittest.TestCase):
    def test_matching_profile_is_ready(self):
        result = run()
        self.assertEqual(result.status, "ready", result)
        comment = render(result, 90, "khaliletanamoh", FILES[0].path, "abcdef1234")
        self.assertTrue(comment.startswith(MARKER))
        self.assertIn("Looks ready for a maintainer", comment)
        self.assertIn("does not verify", comment)

    def test_optional_fields_left_blank_do_not_fail(self):
        files = [ChangedFile("_members/almaz-tesfaye.md")]
        result = review(MINIMAL_FORM, files, MINIMAL_PROFILE, "someone")
        self.assertEqual(result.status, "ready", result)


class UnclearSubmissions(unittest.TestCase):
    def test_name_mismatch_asks_which_spelling(self):
        result = run(profile=PROFILE.replace("name: Khalil Etana\ntitle: Khalil Etana",
                                             "name: Kalil Etana\ntitle: Kalil Etana"))
        self.assertEqual(result.status, "clarify")
        self.assertTrue(any("Which spelling is right" in q for q in result.questions))
        comment = render(result, 90, "khaliletanamoh")
        self.assertIn("@khaliletanamoh", comment)
        self.assertIn("1. ", comment)

    def test_dropped_location_is_flagged(self):
        result = run(profile=PROFILE.replace("location: Shambu, Ethiopia\n", ""))
        self.assertTrue(any("as your location" in q for q in result.questions), result.questions)

    def test_unticked_consent_is_a_question(self):
        result = run(form=FORM.replace("- [x] I am happy", "- [ ] I am happy"))
        self.assertEqual(result.status, "clarify")
        self.assertTrue(any("public website" in q for q in result.questions))
        self.assertFalse(any("community standards" in q for q in result.questions))

    def test_unreadable_link_and_bad_orcid(self):
        form = FORM.replace("https://github.com/khaliletanamoh", "my github is khalil e") \
                   .replace("0009-0005-5740-7324", "0009-0005-5740-7325")
        result = run(form=form)
        self.assertTrue(any("could not be read as a GitHub link" in q for q in result.questions))
        self.assertTrue(any("invalid check digit" in q for q in result.questions))

    def test_fields_not_on_the_form_are_questioned(self):
        profile = MINIMAL_PROFILE.replace("order: 900\n",
                                          "affiliation: Acme\norder: 900\nwebsite: https://a.example\n")
        profile += "\nGeneric developer tagline.\n"
        result = review(MINIMAL_FORM, [ChangedFile("_members/almaz-tesfaye.md")], profile, "x")
        joined = " ".join(result.questions)
        self.assertIn("**Acme** as your affiliation, which was not on the form", joined)
        self.assertIn("personal site", joined)
        self.assertIn("description you did not write", joined)

    def test_missing_membership_and_focus_mismatch(self):
        form = FORM.replace("Student member (bachelor): joining the students chapter", "_No response_")
        result = run(form=form, profile=PROFILE.replace("[models, capacity, linguistics]", "[data]"))
        joined = " ".join(result.questions)
        self.assertIn("membership category", joined)
        self.assertIn("research tracks", joined)

    def test_not_a_form_at_all(self):
        self.assertEqual(run(form="Please add me, I'm Khalil.").status, "clarify")


class AuthorIdentity(unittest.TestCase):
    def test_name_matched_identifiers_need_confirmation(self):
        form = FORM.replace("https://orcid.org/0009-0005-5740-7324", "_No response_")
        profile = WITH_OPENALEX.replace("0009-0005-5740-7324", "0000-0002-1825-0097")
        result = run(form=form, profile=profile, openalex=lambda _: self.fail("no ORCID to compare"))
        self.assertEqual(result.status, "clarify")
        joined = " ".join(result.questions)
        self.assertIn("matched by name only", joined)
        self.assertIn("matched automatically by name", joined)

    def test_openalex_with_matching_orcid_is_only_a_note(self):
        result = run(profile=WITH_OPENALEX, openalex=lambda _: "https://orcid.org/0009-0005-5740-7324")
        self.assertEqual(result.status, "ready", result)
        self.assertTrue(any("consistent" in n for n in result.notes))

    def test_openalex_with_other_or_unknown_orcid_stays_uncertain(self):
        for lookup in (lambda _: None, lambda _: "https://orcid.org/0000-0002-1825-0097"):
            self.assertEqual(run(profile=WITH_OPENALEX, openalex=lookup).status, "clarify")

    def test_submitting_for_someone_else_asks_for_their_agreement(self):
        result = run(author="a-friend")
        self.assertTrue(any("agreed to be listed" in q for q in result.questions))

    def test_orcid_checksum(self):
        self.assertTrue(orcid_checksum_ok("0000-0002-1825-0097"))
        self.assertTrue(orcid_checksum_ok("0000-0002-1694-233X"))
        self.assertFalse(orcid_checksum_ok("0000-0002-1825-0098"))


class ChangedSubmissions(unittest.TestCase):
    def test_extra_files_and_overwrites_need_a_maintainer(self):
        files = [ChangedFile("_members/khalil-etana.md", "modified"), ChangedFile("_config.yml", "modified")]
        result = run(files=files)
        self.assertEqual(result.status, "maintainer")
        self.assertTrue(any("_config.yml" in c for c in result.checks))
        self.assertTrue(any("already exists" in c for c in result.checks))

    def test_hand_added_keys_need_a_maintainer(self):
        self.assertEqual(run(profile=PROFILE.replace("order: 900", "order: 1\nfounder: true")).status,
                         "maintainer")

    def test_invalid_front_matter(self):
        self.assertEqual(run(profile="no front matter here").status, "maintainer")


class FakeGitHub(GitHub):
    """Records calls instead of talking to the network."""

    def __init__(self, responses: dict | None = None, comments: list | None = None):
        super().__init__("EthioNLP/ethionlp.github.io", "token")
        self.responses, self.comments, self.calls = responses or {}, comments or [], []

    def call(self, method, path, payload=None):
        self.calls.append((method, path, payload))
        if method == "GET" and "/comments" in path:
            return self.comments if "page=1" in path else []
        if method == "GET":
            for prefix, value in self.responses.items():
                if path.startswith(self.repo_path(prefix)):
                    return value
            raise AssertionError(f"unexpected GET {path}")
        return {}

    def writes(self):
        return [(m, p) for m, p, _ in self.calls if m != "GET"]


def pull(ref="contrib/issue-90", repo="EthioNLP/ethionlp.github.io", state="open"):
    return {"number": 91, "state": state,
            "head": {"ref": ref, "sha": "abcdef1234", "repo": {"full_name": repo}}}


def join_api(form=FORM, labels=("join",)):
    return {
        "/issues/90": {"body": form, "labels": [{"name": n} for n in labels],
                       "user": {"login": "khaliletanamoh"}},
        "/pulls/91/files": [{"filename": "_members/khalil-etana.md", "status": "added"}],
        "/contents/": {"content": base64.b64encode(PROFILE.encode()).decode()},
    }


class Comments(unittest.TestCase):
    def test_posts_one_comment_and_never_approves(self):
        gh = FakeGitHub(join_api())
        review_pull_request(gh, pull())
        writes = gh.writes()
        self.assertEqual(writes, [("POST", gh.repo_path("/issues/91/comments"))])
        self.assertIn("Looks ready", gh.calls[-1][2]["body"])

    def test_edited_submission_updates_the_comment_and_drops_duplicates(self):
        old = {"id": 1, "user": {"type": "Bot"}, "body": MARKER + "\nold"}
        dup = {"id": 2, "user": {"type": "Bot"}, "body": MARKER + "\nold"}
        human = {"id": 3, "user": {"type": "User"}, "body": MARKER + " quoted by a person"}
        gh = FakeGitHub(join_api(form=FORM.replace("- [x] I am happy", "- [ ] I am happy")),
                        [old, dup, human])
        review_pull_request(gh, pull())
        writes = gh.writes()
        self.assertEqual(writes, [("DELETE", gh.repo_path("/issues/comments/2")),
                                  ("PATCH", gh.repo_path("/issues/comments/1"))])
        self.assertIn("Needs clarification", gh.calls[-1][2]["body"])

    def test_unchanged_comment_is_left_alone(self):
        gh = FakeGitHub(comments=[{"id": 1, "user": {"type": "Bot"}, "body": MARKER + "\nsame"}])
        self.assertEqual(upsert_comment(gh, 91, MARKER + "\nsame"), "unchanged")
        self.assertEqual(gh.writes(), [])


class UnrelatedPullRequests(unittest.TestCase):
    def test_other_branches_forks_and_closed_are_skipped(self):
        for request in (pull(ref="feature/x"), pull(repo="someone/fork"), pull(state="closed")):
            gh = FakeGitHub()
            review_pull_request(gh, request)
            self.assertEqual(gh.calls, [])

    def test_non_join_issue_is_skipped(self):
        gh = FakeGitHub(join_api(form="### Headline\n\nNews", labels=("news",)))
        review_pull_request(gh, pull())
        self.assertEqual(gh.writes(), [])

    def test_join_issue_detection(self):
        self.assertTrue(is_join_issue("", ["join"]))
        self.assertTrue(is_join_issue(FORM, []))
        self.assertFalse(is_join_issue("### Headline", ["news"]))


if __name__ == "__main__":
    unittest.main()
