/* EthioNLP, generic client-side filter.
 *
 * Binds every [data-filter-root] on the page. It knows nothing about members,
 * models or papers: a page declares its facets in markup and this file does the
 * matching. That is why the community, ecosystem, publications and events pages
 * all share one implementation.
 *
 * Markup contract
 * ───────────────
 *   [data-filter-root]                 wrapper for one filter + its items
 *     [data-filter-search]             <input>, matches against item text
 *     [data-facet="<key>"]             <button> toggle; value in data-value
 *                                      data-mode="single" on its .facet-group
 *                                      makes the group radio-like
 *     [data-filter-sort]               <select>, options carry data-key/data-dir
 *     [data-filter-count]              element that receives "N of M"
 *     [data-filter-item]               a filterable item
 *       data-<key>                     space-separated values matched by facets
 *       data-search                    text searched (falls back to textContent)
 *       data-sort-<key>                sort key values
 *     [data-filter-group]              optional wrapper (e.g. a year heading +
 *                                      its items) hidden when all its items are
 *     [data-filter-empty]              shown when nothing matches
 *
 * State is mirrored into the URL query string so a filtered view is linkable.
 */
(function () {
  "use strict";

  function normalise(s) {
    return (s || "").toLowerCase().normalize("NFKD").replace(/[̀-ͯ]/g, "");
  }

  function initRoot(root) {
    var items = Array.prototype.slice.call(root.querySelectorAll("[data-filter-item]"));
    var groups = Array.prototype.slice.call(root.querySelectorAll("[data-filter-group]"));
    var searchInput = root.querySelector("[data-filter-search]");
    var searchWrap = searchInput ? searchInput.closest(".search") : null;
    var clearBtn = root.querySelector("[data-filter-clear]");
    var countEl = root.querySelector("[data-filter-count]");
    var emptyEl = root.querySelector("[data-filter-empty]");
    var sortEl = root.querySelector("[data-filter-sort]");
    var facetBtns = Array.prototype.slice.call(root.querySelectorAll("[data-facet]"));

    // Cache the searchable text once, recomputing textContent per keystroke on
    // a few hundred nodes is the one thing here that would actually be slow.
    items.forEach(function (item) {
      item._search = normalise(item.getAttribute("data-search") || item.textContent);
    });

    var active = {}; // facet key -> Set of selected values

    function facetsFor(key) {
      return facetBtns.filter(function (b) { return b.getAttribute("data-facet") === key; });
    }

    function itemMatchesFacet(item, key, values) {
      if (!values || values.size === 0) return true;
      var raw = item.getAttribute("data-" + key) || "";
      var own = raw.split(/\s+/).filter(Boolean);
      for (var i = 0; i < own.length; i++) {
        if (values.has(own[i])) return true;
      }
      return false;
    }

    function apply() {
      var q = normalise(searchInput ? searchInput.value.trim() : "");
      var terms = q ? q.split(/\s+/) : [];
      var shown = 0;
      // Whether the reader has narrowed anything at all; collapsed groups are
      // only forced open while that is true. Counting keys is not enough:
      // `active` is seeded with an empty Set per facet when the buttons are
      // wired up, so it is never empty. Only a non-empty Set means a choice.
      var filtering = terms.length > 0;
      if (!filtering) {
        for (var k in active) {
          if (active[k] && active[k].size) { filtering = true; break; }
        }
      }

      items.forEach(function (item) {
        var ok = true;

        for (var key in active) {
          if (!itemMatchesFacet(item, key, active[key])) { ok = false; break; }
        }

        if (ok && terms.length) {
          for (var i = 0; i < terms.length; i++) {
            if (item._search.indexOf(terms[i]) === -1) { ok = false; break; }
          }
        }

        item.classList.toggle("is-hidden", !ok);
        if (ok) shown++;

        // An item may control a detail panel that is not itself a filter item.
        // Closing it with its row stops a panel outliving the row that opened
        // it, which otherwise left an expanded language stranded in the middle
        // of a filtered table.
        var panelId = item.getAttribute("data-expand");
        if (panelId && !ok) {
          var panel = document.getElementById(panelId);
          if (panel && !panel.hidden) {
            panel.hidden = true;
            item.classList.remove("is-open");
            var trigger = item.querySelector("[aria-expanded]");
            if (trigger) trigger.setAttribute("aria-expanded", "false");
          }
        }
      });

      groups.forEach(function (g) {
        var visible = g.querySelectorAll("[data-filter-item]:not(.is-hidden)").length;
        g.classList.toggle("is-empty", visible === 0);

        // A collapsed <details> would hide its matches, so a search would look
        // as though it had found nothing. Open any group holding a match while
        // a filter is active, and restore the original state when it clears.
        if (g.tagName === "DETAILS") {
          if (g.dataset.wasOpen === undefined) g.dataset.wasOpen = String(g.open);
          if (filtering) g.open = visible > 0;
          else g.open = g.dataset.wasOpen === "true";
        }
      });

      if (countEl) {
        var noun = countEl.getAttribute("data-noun") || "results";
        // "1 events" reads as a bug even when the number is right.
        if (items.length === 1 && noun.slice(-1) === "s") noun = noun.slice(0, -1);
        countEl.textContent = shown === items.length
          ? items.length + " " + noun
          : shown + " of " + items.length;
      }
      if (emptyEl) emptyEl.hidden = shown !== 0;
      if (searchWrap) searchWrap.classList.toggle("has-value", !!q);

      syncUrl(q);
    }

    function syncUrl(q) {
      if (!window.history || !window.history.replaceState) return;
      var params = new URLSearchParams();
      if (q) params.set("q", q);
      for (var key in active) {
        if (active[key].size) params.set(key, Array.from(active[key]).join(","));
      }
      var qs = params.toString();
      // The fragment is carried through. Rewriting the URL without it drops
      // whatever the visitor followed to get here, and on this page that is a
      // link to one language inside the list.
      var url = (qs ? "?" + qs : location.pathname) + location.hash;
      history.replaceState(null, "", url);
    }

    /* ── Facets ─────────────────────────────────────────────────────────── */
    facetBtns.forEach(function (btn) {
      var key = btn.getAttribute("data-facet");
      var value = btn.getAttribute("data-value");
      if (!active[key]) active[key] = new Set();

      btn.addEventListener("click", function () {
        var group = btn.closest(".facet-group");
        var single = group && group.getAttribute("data-mode") === "single";
        var on = btn.getAttribute("aria-pressed") === "true";

        if (single) {
          facetsFor(key).forEach(function (b) { b.setAttribute("aria-pressed", "false"); });
          active[key].clear();
          if (!on && value) { active[key].add(value); btn.setAttribute("aria-pressed", "true"); }
        } else if (on) {
          active[key].delete(value);
          btn.setAttribute("aria-pressed", "false");
        } else {
          active[key].add(value);
          btn.setAttribute("aria-pressed", "true");
        }
        apply();
      });
    });

    /* ── Search ─────────────────────────────────────────────────────────── */
    if (searchInput) {
      var timer;
      searchInput.addEventListener("input", function () {
        clearTimeout(timer);
        timer = setTimeout(apply, 110);
      });
      searchInput.addEventListener("keydown", function (e) {
        if (e.key === "Escape") { searchInput.value = ""; apply(); }
      });
    }
    if (clearBtn) {
      clearBtn.addEventListener("click", function () {
        if (searchInput) { searchInput.value = ""; searchInput.focus(); }
        apply();
      });
    }

    /* ── Sorting ────────────────────────────────────────────────────────── */
    if (sortEl) {
      sortEl.addEventListener("change", function () {
        var opt = sortEl.options[sortEl.selectedIndex];
        var key = opt.getAttribute("data-key");
        var dir = opt.getAttribute("data-dir") === "asc" ? 1 : -1;
        var parent = items.length ? items[0].parentNode : null;
        if (!parent || !key) return;

        items.slice().sort(function (a, b) {
          var av = a.getAttribute("data-sort-" + key) || "";
          var bv = b.getAttribute("data-sort-" + key) || "";
          var an = parseFloat(av), bn = parseFloat(bv);
          if (!isNaN(an) && !isNaN(bn)) return (an - bn) * dir;
          return av.localeCompare(bv) * dir;
        }).forEach(function (el) { parent.appendChild(el); });
      });
    }

    /* ── Restore state from the URL ─────────────────────────────────────── */
    var params = new URLSearchParams(location.search);
    if (searchInput && params.get("q")) searchInput.value = params.get("q");
    facetBtns.forEach(function (btn) {
      var key = btn.getAttribute("data-facet");
      var wanted = (params.get(key) || "").split(",").filter(Boolean);
      if (wanted.indexOf(btn.getAttribute("data-value")) !== -1) {
        btn.setAttribute("aria-pressed", "true");
        active[key].add(btn.getAttribute("data-value"));
      }
    });

    apply();
  }

  document.querySelectorAll("[data-filter-root]").forEach(initRoot);
})();
