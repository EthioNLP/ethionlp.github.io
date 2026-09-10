# EthioNLP site: local development helpers.
#
#   make serve         build + serve on http://localhost:4000 with live reload
#   make build         one-off build into _site/
#   make sync          refresh every generated file in _data/generated/
#   make member URL=…  scaffold a member file from a profile URL
#   make clean         remove build output
#
# macOS ships Ruby 2.6, which is too old for this Gemfile. Homebrew's ruby@3.4
# is keg-only, so these targets put it on PATH for you:
#     brew install ruby@3.4
#
# Nothing in this file talks to git.

RUBY_PREFIX := $(shell brew --prefix ruby@3.4 2>/dev/null)
ifeq ($(RUBY_PREFIX),)
RUBY_PREFIX := /opt/homebrew/opt/ruby@3.4
endif

BUNDLE := PATH="$(RUBY_PREFIX)/bin:$$PATH" bundle
PORT   ?= 4000
PY     ?= python3
REPO   ?= EthioNLP/ethionlp.github.io

.PHONY: help check-ruby install serve build build-prod clean \
        sync sync-hf sync-pubs sync-github sync-progress sync-catalog sync-expertise \
        member pending scan-events collect-news deps

help:
	@echo "make serve         serve the site at http://localhost:$(PORT)"
	@echo "make build         build the site into _site/"
	@echo "make build-prod    production build (as deployed) into _site_prod/"
	@echo "make sync          refresh all generated data (HF, publications, GitHub, progress)"
	@echo "make member URL=…  scaffold _members/<slug>.md from a profile URL"
	@echo "make pending       who is awaiting confirmation, and the text to send"
	@echo "make clean         remove build output"

check-ruby:
	@test -x "$(RUBY_PREFIX)/bin/ruby" || { \
		echo "Ruby 3.4 not found at $(RUBY_PREFIX)."; \
		echo "Install it with:  brew install ruby@3.4"; \
		exit 1; }
	@echo "Using $$($(RUBY_PREFIX)/bin/ruby -v)"

install: check-ruby
	@$(BUNDLE) config set --local path vendor/bundle >/dev/null 2>&1 || true
	@$(BUNDLE) check >/dev/null 2>&1 || $(BUNDLE) install

serve: install
	$(BUNDLE) exec jekyll serve --port $(PORT) --livereload \
		--livereload-port $$(( $(PORT) + 31729 ))

build: install
	$(BUNDLE) exec jekyll build

build-prod: install
	JEKYLL_ENV=production PAGES_REPO_NWO=$(REPO) $(BUNDLE) exec jekyll build -d _site_prod

# ─── Data sync ────────────────────────────────────────────────────────────────
deps:
	$(PY) -m pip install --quiet --upgrade -r scripts/requirements.txt

sync: sync-hf sync-github sync-pubs sync-progress sync-catalog sync-expertise
	@echo "All generated data refreshed. Review with: git diff _data/generated"

sync-hf:
	$(PY) scripts/sync_huggingface.py

sync-pubs:
	$(PY) scripts/sync_publications.py
	$(PY) scripts/classify_publications.py

sync-github:
	$(PY) scripts/sync_github.py

sync-progress:
	$(PY) scripts/sync_progress.py

# The catalogue of Ethiopian languages (Glottolog + Wikidata + OpenAlex).
sync-catalog:
	$(PY) scripts/sync_catalog.py

# Who works on which language. Reads the other generated files, so it runs last.
sync-expertise:
	$(PY) scripts/sync_expertise.py
	$(PY) scripts/derive_focus.py

# make member URL=https://github.com/someone
# make member URL=https://huggingface.co/someone
member:
	@test -n "$(URL)" || { echo "usage: make member URL=<profile url>"; exit 1; }
	$(PY) scripts/new_member.py "$(URL)"

# Who is known but not yet published, and the text to ask them with.
pending:
	$(PY) scripts/pending_members.py

# Draft news items from the watched events (opens nothing; writes drafts).
scan-events:
	$(PY) scripts/scan_events.py

# Pull news submitted through the shared form and Telegram.
# Needs NEWS_FORM_CSV and/or TELEGRAM_BOT_TOKEN in the environment.
collect-news:
	$(PY) scripts/from_submissions.py

clean:
	rm -rf _site _site_prod .jekyll-cache
