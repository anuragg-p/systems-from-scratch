(function () {
  var root = document.documentElement;
  function setTheme(t) {
    root.setAttribute("data-theme", t);
    try { localStorage.setItem("theme", t); } catch (e) {}
  }
  var tog = document.getElementById("theme");
  if (tog) tog.addEventListener("click", function () {
    setTheme(root.getAttribute("data-theme") === "dark" ? "light" : "dark");
  });

  // Extensions in the sidebar: a disclosure whose state this browser remembers per track
  var extBtn = document.getElementById("ext-toggle"), extBox = document.getElementById("ext");
  if (extBtn && extBox) extBtn.addEventListener("click", function () {
    var open = extBtn.getAttribute("aria-expanded") !== "true";
    extBtn.setAttribute("aria-expanded", open ? "true" : "false");
    document.getElementById("ext-list").hidden = !open;
    try { localStorage.setItem("ext:" + extBox.getAttribute("data-track"), open ? "1" : "0"); } catch (e) {}
  });

  // Navigation drawer (phone)
  var menu = document.getElementById("menu"), scrim = document.getElementById("scrim");
  if (menu) menu.addEventListener("click", function () { document.body.classList.toggle("nav-open"); });
  if (scrim) scrim.addEventListener("click", function () { document.body.classList.remove("nav-open"); });
  // A link to a section of this page (an outline's modules) closes the drawer it was picked from
  document.querySelectorAll('.side a[href^="#"]').forEach(function (a) {
    a.addEventListener("click", function () { document.body.classList.remove("nav-open"); });
  });

  // File tabs in a code block
  var tabs = document.querySelectorAll(".tab[role=tab]");
  tabs.forEach(function (tab) {
    tab.addEventListener("click", function () {
      tabs.forEach(function (t) { t.setAttribute("aria-selected", t === tab ? "true" : "false"); });
      document.querySelectorAll(".file[role=tabpanel]").forEach(function (f) {
        f.classList.toggle("on", f.id === tab.getAttribute("aria-controls"));
      });
    });
  });

  // Copy buttons: the text to copy is in data-copy
  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) return navigator.clipboard.writeText(text);
    return new Promise(function (resolve, reject) {
      var ta = document.createElement("textarea");
      ta.value = text; ta.setAttribute("readonly", ""); ta.style.position = "fixed"; ta.style.opacity = "0";
      document.body.appendChild(ta); ta.select();
      try { document.execCommand("copy") ? resolve() : reject(new Error("copy failed")); } catch (e) { reject(e); }
      document.body.removeChild(ta);
    });
  }
  // Copy page: data-copy-from names a (hidden) textarea whose value is the lesson as Markdown
  function textToCopy(btn) {
    if (btn.hasAttribute("data-copy")) return btn.getAttribute("data-copy");
    var from = document.getElementById(btn.getAttribute("data-copy-from"));
    return from ? from.value : "";
  }
  document.querySelectorAll("[data-copy], [data-copy-from]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var label = btn.querySelector("span"), old = label ? label.textContent : "";
      copyText(textToCopy(btn)).then(function () {
        if (label) label.textContent = "Copied";
      }, function () {
        if (label) label.textContent = "Press Ctrl+C";
      }).then(function () { setTimeout(function () { if (label) label.textContent = old; }, 1600); });
    });
  });

  // Folds: each function body opens and shuts on its own (the chevron on its first line, or the
  // "..." that stands in for a shut one); "Functions only" shuts or opens every one in the code
  // it controls. That choice is remembered, so the next lesson opens the same way. A body the page
  // starts with shut (data-shut: a long list of what a lesson also adds) goes back to shut when
  // "Functions only" is turned off, as it was before it was turned on.
  function setFold(box, shut) {
    box.classList.toggle("shut", shut);
    document.querySelectorAll('.fold-btn[aria-controls="' + box.id + '"]').forEach(function (b) {
      b.setAttribute("aria-expanded", shut ? "false" : "true");
    });
  }
  function setAll(box, shut) {
    if (box) box.querySelectorAll(".fbody").forEach(function (f) { setFold(f, shut || f.hasAttribute("data-shut")); });
  }
  document.addEventListener("click", function (ev) {
    var t = ev.target.closest ? ev.target.closest(".fold-btn, .fold-more") : null;
    if (!t) return;
    var box = document.getElementById(t.getAttribute("aria-controls"));
    if (!box) return;
    setFold(box, !box.classList.contains("shut"));
    if (t.classList.contains("fold-more")) {
      var head = document.querySelector('.fold-btn[aria-controls="' + box.id + '"]');
      if (head) head.focus();
    }
  });
  // A long file with nothing to fold starts as its first lines (the pane is "clipped"):
  // "Show all N lines" opens the rest, and the same button shows the first lines again.
  document.addEventListener("click", function (ev) {
    var t = ev.target.closest ? ev.target.closest(".clip-more") : null;
    if (!t) return;
    var pane = document.getElementById(t.getAttribute("aria-controls"));
    if (!pane) return;
    var open = t.getAttribute("aria-expanded") !== "true";
    pane.classList.toggle("clipped", !open);
    t.setAttribute("aria-expanded", open ? "true" : "false");
    var label = t.querySelector("span");
    if (label) label.textContent = t.getAttribute(open ? "data-less" : "data-more");
  });
  var foldOn = false;
  try { foldOn = localStorage.getItem("fold") === "1"; } catch (e) {}
  document.querySelectorAll("[data-fold-toggle]").forEach(function (btn) {
    function apply(on) {
      btn.setAttribute("aria-pressed", on ? "true" : "false");
      setAll(document.getElementById(btn.getAttribute("aria-controls")), on);
    }
    apply(foldOn);
    btn.addEventListener("click", function () {
      var on = btn.getAttribute("aria-pressed") !== "true";
      apply(on);
      try { localStorage.setItem("fold", on ? "1" : "0"); } catch (e) {}
    });
  });

  // Files drawer: a side panel with the project tree and viewer
  var drawer = document.getElementById("files-drawer"), opener = null;
  function viewer(card) {
    var base = card.getAttribute("data-files"), lesson = card.getAttribute("data-lesson");
    var body = card.querySelector("[data-role=fbody]"), pathEl = card.querySelector("[data-role=fpath]");
    var note = card.querySelector("[data-role=fnote]"), foldBtn = card.querySelector("[data-fold-toggle]");
    var buttons = card.querySelectorAll(".ft-file");
    var seq = 0, started = false;
    // ./learn serve answers each file on request. A static copy (./learn export) has no server:
    // data-index names this lesson's index, {path: URL of the file's view}, read once.
    var indexUrl = card.getAttribute("data-index"), index = null;
    function json(r) {   // the server says what went wrong in JSON; a static host sends an HTML 404
      if (!r.ok && indexUrl) throw new Error("HTTP " + r.status);
      return r.json();
    }
    function load(path) {
      if (!indexUrl) return fetch(base + "?path=" + encodeURIComponent(path) + "&lesson=" + encodeURIComponent(lesson)).then(json);
      index = index || fetch(indexUrl).then(json).catch(function (e) { index = null; throw e; });
      return index.then(function (map) {
        return map[path] ? fetch(map[path]).then(json) : { error: "no such file at this lesson" };
      });
    }
    function openFile(btn) {
      var path = btn.getAttribute("data-path"), mine = ++seq;
      buttons.forEach(function (b) { b.classList.toggle("active", b === btn); });
      pathEl.textContent = path;
      note.textContent = "loading";
      load(path)
        .then(function (j) {
          if (mine !== seq) return;
          if (j.error) { body.innerHTML = ""; note.textContent = j.error; return; }
          body.innerHTML = j.html;
          note.textContent = j.truncated ? "truncated" : (j.note || "");
          if (foldBtn) {
            foldBtn.hidden = !j.foldable;
            if (foldBtn.getAttribute("aria-pressed") === "true") setAll(body, true);
          }
          var band = Array.prototype.find.call(body.querySelectorAll(".row.band"), function (r) { return r.offsetParent !== null; });
          body.scrollTop = band ? Math.max(0, band.offsetTop - 48) : 0;
        }).catch(function (e) { if (mine === seq) note.textContent = "could not load: " + e; });
    }
    buttons.forEach(function (b) { b.addEventListener("click", function () { openFile(b); }); });
    return function first() {
      if (started) return;
      started = true;
      var want = card.getAttribute("data-open");
      if (want) buttons.forEach(function (b) { if (b.getAttribute("data-path") === want) openFile(b); });
    };
  }
  if (drawer) {
    var openFirst = viewer(drawer);
    var focusables = function () {
      return Array.prototype.filter.call(drawer.querySelectorAll("button, [href], input, summary, [tabindex]:not([tabindex='-1'])"),
        function (el) { return !el.disabled && el.offsetParent !== null; });
    };
    var closeDrawer = function () {
      if (drawer.hidden) return;
      drawer.hidden = true;
      document.body.classList.remove("drawer-open");
      if (opener) { opener.setAttribute("aria-expanded", "false"); opener.focus(); }
    };
    document.querySelectorAll("[data-drawer-open]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        opener = btn;
        drawer.hidden = false;
        document.body.classList.add("drawer-open");
        btn.setAttribute("aria-expanded", "true");
        openFirst();
        var panel = drawer.querySelector(".drawer-panel");
        (drawer.querySelector("[data-drawer-close].btn") || panel).focus();
      });
    });
    drawer.querySelectorAll("[data-drawer-close]").forEach(function (el) { el.addEventListener("click", closeDrawer); });
    document.addEventListener("keydown", function (ev) {
      if (drawer.hidden) return;
      if (ev.key === "Escape") { ev.preventDefault(); closeDrawer(); return; }
      if (ev.key === "Tab") {   // keep focus inside the open drawer
        var f = focusables();
        if (!f.length) return;
        var first = f[0], last = f[f.length - 1];
        if (ev.shiftKey && (document.activeElement === first || !drawer.contains(document.activeElement))) { ev.preventDefault(); last.focus(); }
        else if (!ev.shiftKey && document.activeElement === last) { ev.preventDefault(); first.focus(); }
      }
    });
  }

  // Stepped figures (harness/web/art.py): the page holds every frame, one under another, which is
  // what a reader without scripts and a printout get. Here the frames share one place and Back and
  // Next step through them, one at a time, with no wrap-around; Left and Right do the same while
  // the figure has focus. The swap is instant, and the hidden frames keep their place in the
  // layout, so the figure is as tall as its tallest frame and nothing under it moves.
  var chev = function (d) {
    return '<svg class="ic" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="' + d +
      '" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  };
  document.querySelectorAll("figure.steps").forEach(function (fig) {
    var list = fig.querySelector(".steps-list");
    var frames = list ? list.querySelectorAll(".steps-frame") : [];
    if (frames.length < 2) return;
    var n = frames.length, k = 0;
    var bar = document.createElement("div");
    bar.className = "steps-bar";
    bar.innerHTML = '<button class="btn steps-btn" type="button" data-go="-1">' + chev("M10 3L5 8l5 5") + "<span>Back</span></button>" +
      '<p class="steps-now" aria-live="polite" aria-atomic="true"></p>' +
      '<button class="btn steps-btn" type="button" data-go="1"><span>Next</span>' + chev("M6 3l5 5-5 5") + "</button>";
    var back = bar.querySelector('[data-go="-1"]'), next = bar.querySelector('[data-go="1"]'), now = bar.querySelector(".steps-now");
    now.style.minWidth = ("Step " + n + " of " + n).length + "ch";   // the buttons stay put as k grows a digit
    function show(i) {
      k = Math.max(0, Math.min(n - 1, i));
      frames.forEach(function (f, j) { f.classList.toggle("on", j === k); });
      var count = document.createElement("span"), text = frames[k].querySelector(".steps-t");
      count.textContent = "Step " + (k + 1) + " of " + n;
      now.textContent = "";
      now.appendChild(count);
      if (text) {   // read out with the count; the frame shows it already
        var say = document.createElement("span");
        say.className = "steps-sr";
        say.textContent = ": " + text.textContent;
        now.appendChild(say);
      }
      // a disabled button loses focus: hand it to the figure, where the arrow keys still work
      var lost = (document.activeElement === back && k === 0) || (document.activeElement === next && k === n - 1);
      back.disabled = k === 0;
      next.disabled = k === n - 1;
      if (lost) fig.focus();
    }
    show(0);
    list.parentNode.insertBefore(bar, list.nextSibling);
    list.setAttribute("aria-hidden", "true");   // the live line under it says the same
    fig.setAttribute("tabindex", "-1");
    fig.classList.add("is-live");
    bar.addEventListener("click", function (ev) {
      var b = ev.target.closest ? ev.target.closest("[data-go]") : null;
      if (b && !b.disabled) show(k + Number(b.getAttribute("data-go")));
    });
    fig.addEventListener("keydown", function (ev) {
      if (ev.altKey || ev.ctrlKey || ev.metaKey || ev.shiftKey) return;
      if (ev.key !== "ArrowLeft" && ev.key !== "ArrowRight") return;
      ev.preventDefault();
      show(k + (ev.key === "ArrowRight" ? 1 : -1));
    });
  });
})();
