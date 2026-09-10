/* EthioNLP, the language comparison on /languages/.
 *
 * The chart is server-rendered: every language is already a row in the HTML,
 * with its four figures on data- attributes, and the default selection is the
 * only one visible. This file adds the two things markup cannot do, which is
 * choosing which rows are shown and rescaling the bars to that choice.
 *
 * Rescaling is the point. A bar scaled to the catalogue maximum answers "how
 * big is this against Amharic", which for ninety-nine of the hundred languages
 * is a sliver and tells you nothing. Scaled to the current selection it answers
 * "how do these compare with each other", which is the question the control is
 * there to ask.
 */
(function () {
  "use strict";

  var METRICS = ["speakers", "papers", "artifacts", "people"];
  var MIN_W = 2;   // percent, so a non-zero value is never an invisible bar

  function value(el, metric) {
    return parseInt(el.getAttribute("data-" + metric), 10) || 0;
  }

  // Descending, with the name as the tie-break so equal values, of which there
  // are many at zero, keep a stable and predictable order.
  function byMetric(metric) {
    return function (a, b) {
      return value(b, metric) - value(a, metric) ||
             (a.id || a.getAttribute("data-key") || "").localeCompare(
               b.id || b.getAttribute("data-key") || "");
    };
  }

  function wireSort(scope, apply) {
    var buttons = scope.querySelectorAll("[data-cmp-sort]");
    Array.prototype.forEach.call(buttons, function (btn) {
      btn.addEventListener("click", function () {
        Array.prototype.forEach.call(buttons, function (other) {
          other.setAttribute("aria-pressed", String(other === btn));
        });
        apply(btn.getAttribute("data-cmp-sort"));
      });
    });
  }

  /* ── The full catalogue list ──────────────────────────────────────────────
   * No picker and no rescaling: every language is shown, so the bars are
   * already scaled to the catalogue and stay put when the filter narrows the
   * list. All this adds is sorting.
   */
  Array.prototype.forEach.call(
    document.querySelectorAll("[data-cmp-static]"),
    function (list) {
      var items = Array.prototype.slice.call(list.querySelectorAll("[data-cmp-item]"));
      if (!items.length) return;

      wireSort(list, function (metric) {
        items.slice().sort(byMetric(metric)).forEach(function (item) {
          list.appendChild(item);
        });
      });
    }
  );

  // Following a link to one language has to open the fold it lives in as well
  // as the row itself, or it scrolls to a collapsed section and looks broken.
  function revealTarget() {
    var id = location.hash.slice(1);
    if (!id) return;
    var target = document.getElementById(id);
    if (!target) return;

    var node = target;
    while (node) {
      if (node.tagName === "DETAILS") node.open = true;
      node = node.parentElement;
    }
    target.scrollIntoView();
  }

  window.addEventListener("hashchange", revealTarget);
  revealTarget();

  /* ── The ranked chart ─────────────────────────────────────────────────────
   * A hundred numbered bars, ordered by what has been released. The order is
   * settled here rather than in the template because the sort key is
   * models + datasets, and Liquid cannot sort on a computed sum.
   *
   * The numbering follows the sort, so bar 1 is always the best-resourced
   * language, and the legend is reordered to match. Without JavaScript the
   * bars still render, in catalogue order, with sequential numbers: the chart
   * is then a picture of the same data, just not ranked.
   */
  var rank = document.querySelector(".rank");
  if (rank) {
    var bars = Array.prototype.slice.call(rank.querySelectorAll("[data-rank-open]"))
      .filter(function (el) { return el.classList.contains("rank__bar"); });
    var legend = rank.querySelector(".rank__legend");
    var items = Array.prototype.slice.call(legend ? legend.children : []);

    var key = function (el) {
      return [parseInt(el.getAttribute("data-sort-res"), 10) || 0,
              parseInt(el.getAttribute("data-sort-pa"), 10) || 0];
    };
    var order = bars.slice().sort(function (a, b) {
      var ka = key(a), kb = key(b);
      return (kb[0] - ka[0]) || (kb[1] - ka[1]);
    });

    var seat = {};
    order.forEach(function (bar, i) {
      var n = bar.querySelector(".rank__n");
      if (n) n.textContent = i + 1;
      seat[bar.getAttribute("data-rank-open")] = i + 1;
      bar.parentNode.appendChild(bar);
    });

    // The legend is the key to the numbers, so it has to carry them and follow
    // the same order; a legend in a different order is worse than none.
    items.forEach(function (li) {
      var b = li.querySelector("[data-rank-open]");
      if (!b) return;
      var n = seat[b.getAttribute("data-rank-open")];
      if (n) li.setAttribute("value", n);
    });
    items.sort(function (a, b) {
      return (a.getAttribute("value") || 0) - (b.getAttribute("value") || 0);
    }).forEach(function (li) { legend.appendChild(li); });
  }

  // Either half of the chart shows the entry's detail, in place.
  //
  // Earlier this scrolled to the row in the list below, which meant a jump of
  // some four thousand pixels away from the chart you were reading. The detail
  // is cloned up to the chart instead; the list stays where it is for anyone
  // who wants to browse it.
  // Named for the chart, not just "panel": the comparison picker further down
  // declares its own `var panel`, and in a shared function scope `var` hoists
  // to a single binding, so two declarations of that name resolve to one
  // element. Keep these two names distinct.
  var rankPanel = document.querySelector(".rank__detail");

  document.addEventListener("click", function (e) {
    var hit = e.target.closest("[data-rank-open]");
    if (!hit || !rankPanel) return;

    var slug = hit.getAttribute("data-rank-open");
    var row = document.getElementById(slug);
    var body = row && row.querySelector(".cmp__detail");
    if (!body) return;

    var name = row.querySelector(".cmp__langname");
    var summary = row.querySelector(".cmp__row");

    rankPanel.textContent = "";
    var head = document.createElement("div");
    head.className = "rank__detailhead";
    var h = document.createElement("h3");
    h.textContent = name ? name.textContent.trim() : slug;
    head.appendChild(h);

    // The figures already sit in the row's own summary; lifting them keeps the
    // panel self-contained rather than making the reader look in two places.
    if (summary) {
      var figures = document.createElement("p");
      figures.className = "rank__figures";
      Array.prototype.forEach.call(summary.querySelectorAll(".cmp__metric"), function (m) {
        var label = m.getAttribute("data-label");
        var value = m.querySelector(".cmp__val");
        var text = value ? value.textContent.trim() : "";
        if (!text) return;
        var span = document.createElement("span");
        span.textContent = label + " " + text;
        figures.appendChild(span);
      });
      if (figures.childNodes.length) head.appendChild(figures);
    }

    var close = document.createElement("button");
    close.type = "button";
    close.className = "rank__close";
    close.setAttribute("aria-label", "Close");
    close.textContent = "\u00d7";
    close.addEventListener("click", function () {
      rankPanel.hidden = true;
      rankPanel.textContent = "";
    });
    head.appendChild(close);

    rankPanel.appendChild(head);
    rankPanel.appendChild(body.cloneNode(true));
    rankPanel.hidden = false;

    Array.prototype.forEach.call(document.querySelectorAll(".rank__bar.is-picked"),
      function (el) { el.classList.remove("is-picked"); });
    var bar = document.querySelector('.rank__bar[data-rank-open="' + slug + '"]');
    if (bar) bar.classList.add("is-picked");
  });

  /* ── The comparison ───────────────────────────────────────────────────── */

  var root = document.querySelector("[data-compare]");
  if (!root) return;

  var picker = root.querySelector("[data-compare-picker]");
  var chips = root.querySelector("[data-compare-chips]");
  var openBtn = root.querySelector("[data-compare-open]");
  var panel = root.querySelector("[data-compare-panel]");
  var search = root.querySelector("[data-compare-search]");
  var none = root.querySelector("[data-compare-none]");
  var chart = root.querySelector("[data-compare-chart]");
  var empty = root.querySelector("[data-compare-empty]");

  var rows = Array.prototype.slice.call(root.querySelectorAll("[data-cmp-row]"));
  var boxes = Array.prototype.slice.call(root.querySelectorAll("[data-picker-opt] input"));
  var opts = Array.prototype.slice.call(root.querySelectorAll("[data-picker-opt]"));

  if (!rows.length || !boxes.length) return;

  var byKey = {};
  rows.forEach(function (row) { byKey[row.getAttribute("data-key")] = row; });

  var sortBy = "papers";

  function selected() {
    return boxes.filter(function (b) { return b.checked; });
  }

  /* ── The chart ────────────────────────────────────────────────────────── */

  function render() {
    var chosen = selected();
    var keys = {};
    chosen.forEach(function (b) { keys[b.value] = true; });

    var shown = rows.filter(function (row) {
      var on = !!keys[row.getAttribute("data-key")];
      row.hidden = !on;
      return on;
    });

    // One maximum per metric, over the selection only.
    var max = {};
    METRICS.forEach(function (m) {
      max[m] = shown.reduce(function (a, row) { return Math.max(a, value(row, m)); }, 0);
    });

    shown.forEach(function (row) {
      METRICS.forEach(function (m) {
        var bar = row.querySelector('[data-metric="' + m + '"] .cmp__bar');
        if (!bar) return;
        var v = value(row, m);
        // A zero stays a zero; anything else gets at least a visible sliver.
        var pct = !v || !max[m] ? 0 : Math.max(MIN_W, (v / max[m]) * 100);
        bar.style.setProperty("--w", pct.toFixed(1) + "%");
      });
    });

    // Sorting moves the rows themselves, so the order survives the next render.
    shown.sort(byMetric(sortBy)).forEach(function (row) { chart.appendChild(row); });

    if (empty) {
      empty.hidden = shown.length > 0;
      chart.appendChild(empty);
    }
    renderChips(shown);
  }

  /* ── Chips ────────────────────────────────────────────────────────────── */

  // Chips follow the chart's order rather than the catalogue's, so the first
  // chip is the first row and the two read as one thing.
  function renderChips(shown) {
    if (!chips) return;
    chips.textContent = "";

    shown.forEach(function (row) {
      var key = row.getAttribute("data-key");
      var box = boxes.filter(function (b) { return b.value === key; })[0];
      if (!box) return;
      var name = row.querySelector(".cmp__name a").textContent.trim();

      var li = document.createElement("li");
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "chip chip--removable";
      btn.setAttribute("aria-label", "Remove " + name);
      btn.appendChild(document.createTextNode(name));

      var x = document.createElement("span");
      x.className = "chip__x";
      x.setAttribute("aria-hidden", "true");
      x.textContent = "×";
      btn.appendChild(x);

      btn.addEventListener("click", function () {
        box.checked = false;
        render();
      });

      li.appendChild(btn);
      chips.appendChild(li);
    });

    if (!shown.length) {
      var note = document.createElement("li");
      note.className = "picker__placeholder";
      note.textContent = "No languages selected";
      chips.appendChild(note);
    }
  }

  /* ── The panel ────────────────────────────────────────────────────────── */

  function setOpen(open) {
    if (!panel || !openBtn) return;
    panel.hidden = !open;
    openBtn.setAttribute("aria-expanded", String(open));
    if (open && search) search.focus();
  }

  if (openBtn && panel) {
    openBtn.addEventListener("click", function () {
      setOpen(panel.hidden);
    });

    document.addEventListener("click", function (e) {
      if (panel.hidden) return;
      if (!picker.contains(e.target)) setOpen(false);
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && !panel.hidden) {
        setOpen(false);
        openBtn.focus();
      }
    });
  }

  if (search) {
    search.addEventListener("input", function () {
      var q = search.value.trim().toLowerCase();
      var hits = 0;
      opts.forEach(function (opt) {
        var ok = !q || opt.getAttribute("data-search").toLowerCase().indexOf(q) > -1;
        opt.hidden = !ok;
        if (ok) hits++;
      });
      if (none) none.hidden = hits > 0;
    });
  }

  boxes.forEach(function (box) {
    box.addEventListener("change", render);
  });

  /* ── Sorting ──────────────────────────────────────────────────────────── */

  wireSort(chart, function (metric) {
    sortBy = metric;
    render();
  });

  // Only now: with the script running, the controls do something.
  if (picker) picker.hidden = false;
  render();
})();
