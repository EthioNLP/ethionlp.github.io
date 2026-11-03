/* EthioNLP, site chrome.
 *
 * Deliberately small and dependency-free: theme toggle, mobile nav, the
 * multilingual hero rotator and the sticky-header shadow. Everything else on
 * the site is server-rendered.
 */
(function () {
  "use strict";

  var THEME_KEY = "ethionlp-theme";
  var root = document.documentElement;

  /* ── Theme ────────────────────────────────────────────────────────────── */
  var toggle = document.getElementById("theme-toggle");
  if (toggle) {
    toggle.addEventListener("click", function () {
      var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem(THEME_KEY, next); } catch (e) {}
    });
  }

  /* ── Mobile navigation ────────────────────────────────────────────────── */
  var header = document.getElementById("site-header");
  var burger = document.getElementById("nav-burger");

  if (burger && header) {
    burger.addEventListener("click", function () {
      var open = header.classList.toggle("is-open");
      burger.setAttribute("aria-expanded", String(open));
      burger.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && header.classList.contains("is-open")) {
        burger.click();
        burger.focus();
      }
    });

    // A tap on a link inside the drawer should close it.
    header.addEventListener("click", function (e) {
      if (e.target.closest(".nav__links a") && header.classList.contains("is-open")) {
        header.classList.remove("is-open");
        burger.setAttribute("aria-expanded", "false");
      }
    });
  }

  /* ── Header dropdowns ─────────────────────────────────────────────────────
   * Click to open, not hover. Escape and an outside click close; on mobile the
   * groups are flattened by CSS and these buttons are inert (pointer-events:
   * none), so this code simply never fires there.
   */
  var parents = document.querySelectorAll(".nav__parent");

  function closeMenus(except) {
    Array.prototype.forEach.call(parents, function (p) {
      if (p !== except) p.setAttribute("aria-expanded", "false");
    });
  }

  Array.prototype.forEach.call(parents, function (parent) {
    parent.addEventListener("click", function (e) {
      e.stopPropagation();
      var open = parent.getAttribute("aria-expanded") === "true";
      closeMenus(parent);
      parent.setAttribute("aria-expanded", String(!open));
    });

    // On a pointer device CSS already opens the menu on hover. Clearing the
    // clicked-open state when the pointer leaves stops a menu that was clicked
    // from staying pinned open after the mouse has moved away.
    var group = parent.closest(".nav__group");
    if (group) {
      group.addEventListener("mouseleave", function () {
        parent.setAttribute("aria-expanded", "false");
      });
    }
  });

  /* A two-column menu is wide enough to run off the right of the window when
   * its parent sits near the end of the nav. Measure once per menu, on first
   * reveal, and flip it to right-aligned if it would overflow. Done in JS
   * because CSS cannot ask "would this overflow?".
   */
  function keepMenuOnScreen(group) {
    var menu = group.querySelector(".nav__menu");
    if (!menu || menu.dataset.placed) return;

    // Measure against the untransformed position; the menu is laid out even
    // while hidden, so no reflow trickery is needed.
    var box = menu.getBoundingClientRect();
    if (box.right > document.documentElement.clientWidth - 8) {
      menu.classList.add("nav__menu--right");
    }
    menu.dataset.placed = "1";
  }

  // Measured on first reveal rather than on load. A closed menu is display:
  // none and has no box to measure; by the time either of these fires the CSS
  // has already shown it, so the rect is real and the class lands before the
  // browser paints. Nothing here runs before the menu is wanted, so there is no
  // window in which a mis-placed menu can widen the page.
  Array.prototype.forEach.call(parents, function (parent) {
    var group = parent.closest(".nav__group");
    if (!group) return;
    group.addEventListener("mouseenter", function () { keepMenuOnScreen(group); });
    parent.addEventListener("focus", function () { keepMenuOnScreen(group); });
  });

  // Forget the answer after a resize; it changes with the window, and the next
  // reveal measures again.
  window.addEventListener("resize", function () {
    Array.prototype.forEach.call(document.querySelectorAll(".nav__menu"), function (menu) {
      menu.classList.remove("nav__menu--right");
      delete menu.dataset.placed;
    });
  }, { passive: true });

  if (parents.length) {
    document.addEventListener("click", function (e) {
      if (!e.target.closest(".nav__group")) closeMenus();
    });
    document.addEventListener("keydown", function (e) {
      if (e.key !== "Escape") return;
      var open = document.querySelector('.nav__parent[aria-expanded="true"]');
      if (open) { closeMenus(); open.focus(); }
    });
  }

  /* ── Sticky-header hairline ───────────────────────────────────────────── */
  if (header) {
    var setStuck = function () {
      header.classList.toggle("is-stuck", window.scrollY > 4);
    };
    setStuck();
    window.addEventListener("scroll", setStuck, { passive: true });
  }

  /* ── Hero rotator ─────────────────────────────────────────────────────────
   * Cycles a welcome line through the languages the community works in. The
   * strings live in the markup (data-rotate) so they are in the HTML source
   * for crawlers and for anyone with JS disabled.
   */
  var rotator = document.querySelector("[data-rotate]");
  if (rotator && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    var phrases;
    try {
      phrases = JSON.parse(rotator.getAttribute("data-rotate"));
    } catch (e) {
      phrases = null;
    }

    if (phrases && phrases.length > 1) {
      var i = 0;
      setInterval(function () {
        i = (i + 1) % phrases.length;
        var span = document.createElement("span");
        span.textContent = phrases[i].text;
        if (phrases[i].lang) span.setAttribute("lang", phrases[i].lang);
        rotator.replaceChildren(span);
      }, 3600);
    }
  }

  /* ── Front-page announcements ─────────────────────────────────────────────
   * Shows one announcement at a time. Everything here exists so that rotating
   * content does not cost anyone a link:
   *
   *   - without this script every item is already visible (the CSS default),
   *     so no-JS readers and crawlers see all of them;
   *   - prefers-reduced-motion opts out entirely and leaves them stacked;
   *   - rotation pauses on hover and on focus, so an item cannot slide away
   *     while it is being read or clicked;
   *   - hidden items carry `hidden`, which keeps them out of the tab order,
   *     and focusing anywhere in the rail reveals the focused one.
   */
  var rail = document.querySelector("[data-announce-rotate]");
  if (rail && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    var items = Array.prototype.slice.call(rail.querySelectorAll("[data-announce-item]"));
    var dotWrap = document.querySelector("[data-announce-dots]");
    var dots = dotWrap ? Array.prototype.slice.call(dotWrap.querySelectorAll("[data-announce-dot]")) : [];

    if (items.length > 1) {
      var at = 0;
      var timer = null;
      var INTERVAL = 5000;

      function show(n) {
        at = (n + items.length) % items.length;
        items.forEach(function (el, i) { el.hidden = i !== at; });
        dots.forEach(function (d, i) { d.setAttribute("aria-current", i === at ? "true" : "false"); });
      }
      function start() { stop(); timer = setInterval(function () { show(at + 1); }, INTERVAL); }
      function stop() { if (timer) { clearInterval(timer); timer = null; } }

      rail.classList.add("is-rotating");
      if (dotWrap) dotWrap.hidden = false;
      show(0);
      start();

      rail.addEventListener("mouseenter", stop);
      rail.addEventListener("mouseleave", start);
      rail.addEventListener("focusin", function (e) {
        stop();
        var i = items.indexOf(e.target.closest("[data-announce-item]"));
        if (i > -1) show(i);
      });
      rail.addEventListener("focusout", function (e) {
        if (!rail.contains(e.relatedTarget)) start();
      });
      dots.forEach(function (d, i) {
        d.addEventListener("click", function () { stop(); show(i); });
      });
      // Nothing should keep ticking in a background tab.
      document.addEventListener("visibilitychange", function () {
        if (document.hidden) { stop(); } else { start(); }
      });
    }
  }

  /* ── Gallery lightbox ─────────────────────────────────────────────────────
   * A native <dialog>, so Escape, the backdrop and focus handling come from the
   * platform. Browsers without dialog support simply follow nothing and the
   * grid still works, the full-size image is the same file already on screen.
   */
  var lightbox = null;

  function openLightbox(src, caption) {
    if (!window.HTMLDialogElement) return;

    if (!lightbox) {
      lightbox = document.createElement("dialog");
      lightbox.className = "lightbox";
      lightbox.innerHTML =
        '<button class="lightbox__close" type="button" aria-label="Close">' +
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" ' +
        'stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18"/></svg>' +
        '</button><img alt=""><p class="lightbox__cap"></p>';

      lightbox.querySelector(".lightbox__close")
              .addEventListener("click", function () { lightbox.close(); });

      // Clicking the backdrop closes; clicking the image does not.
      lightbox.addEventListener("click", function (e) {
        if (e.target === lightbox) lightbox.close();
      });

      document.body.appendChild(lightbox);
    }

    lightbox.querySelector("img").src = src;
    lightbox.querySelector("img").alt = caption || "";
    lightbox.querySelector(".lightbox__cap").textContent = caption || "";
    lightbox.showModal();
  }

  document.addEventListener("click", function (e) {
    var trigger = e.target.closest("[data-lightbox]");
    if (!trigger) return;
    openLightbox(trigger.getAttribute("data-lightbox"),
                 trigger.getAttribute("data-lightbox-caption"));
  });

  /* ── Sortable tables ──────────────────────────────────────────────────────
   * Progressive: the table is already in a sensible order server-side, and
   * clicking a header only reorders what is there. Numeric columns sort on a
   * data-value attribute so that "1.2M" and "" still order correctly.
   */
  Array.prototype.forEach.call(document.querySelectorAll("[data-sortable]"), function (table) {
    var body = table.tBodies[0];
    if (!body) return;

    Array.prototype.forEach.call(table.querySelectorAll("th[data-sort]"), function (th, col) {
      th.setAttribute("tabindex", "0");
      th.setAttribute("role", "button");

      function sort() {
        var numeric = th.getAttribute("data-sort") === "num";
        var descending = th.getAttribute("aria-sort") !== "descending";

        Array.prototype.forEach.call(table.querySelectorAll("th[data-sort]"), function (other) {
          other.removeAttribute("aria-sort");
        });
        th.setAttribute("aria-sort", descending ? "descending" : "ascending");

        var rows = Array.prototype.slice.call(body.rows);
        rows.sort(function (a, b) {
          var x = a.cells[col], y = b.cells[col];
          if (!x || !y) return 0;

          if (numeric) {
            var nx = parseFloat(x.getAttribute("data-value"));
            var ny = parseFloat(y.getAttribute("data-value"));
            if (isNaN(nx)) nx = -Infinity;
            if (isNaN(ny)) ny = -Infinity;
            return descending ? ny - nx : nx - ny;
          }
          var sx = x.textContent.trim(), sy = y.textContent.trim();
          return descending ? sy.localeCompare(sx) : sx.localeCompare(sy);
        });

        var frag = document.createDocumentFragment();
        rows.forEach(function (r) { frag.appendChild(r); });
        body.appendChild(frag);
      }

      th.addEventListener("click", sort);
      th.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); sort(); }
      });
    });
  });

  /* ── Expandable table rows ────────────────────────────────────────────────
   * A row in the language catalogue opens a panel naming the models, datasets
   * and people behind its numbers. The panel is in the HTML already; this only
   * toggles it, so the content is there for search and for anyone without
   * JavaScript, who simply sees the table.
   */
  Array.prototype.forEach.call(document.querySelectorAll("tr[data-expand]"), function (row) {
    var panel = document.getElementById(row.getAttribute("data-expand"));
    if (!panel) return;

    var cell = row.querySelector("th");
    if (cell) {
      cell.setAttribute("tabindex", "0");
      cell.setAttribute("role", "button");
      cell.setAttribute("aria-expanded", "false");
      cell.setAttribute("aria-controls", panel.id);
      cell.classList.add("is-expandable");
    }

    function toggle() {
      var open = !panel.hidden;
      panel.hidden = open;
      row.classList.toggle("is-open", !open);
      if (cell) cell.setAttribute("aria-expanded", String(!open));
    }

    row.addEventListener("click", function (e) {
      // Let a real link inside the row do its own job.
      if (e.target.closest("a, details, summary")) return;
      toggle();
    });

    if (cell) {
      cell.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); }
      });
    }
  });

  /* ── Copy-to-clipboard buttons ────────────────────────────────────────── */
  document.addEventListener("click", function (e) {
    var btn = e.target.closest("[data-copy]");
    if (!btn || !navigator.clipboard) return;

    navigator.clipboard.writeText(btn.getAttribute("data-copy")).then(function () {
      var original = btn.textContent;
      btn.textContent = "Copied";
      setTimeout(function () { btn.textContent = original; }, 1400);
    });
  });
})();
