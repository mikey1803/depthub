// DeptHub: dark mode toggle, live countdowns, entrance reveal. No libraries.
(function () {
  var root = document.documentElement;

  // ----- dark mode (choice remembered in localStorage) -----
  var toggle = document.getElementById("theme-toggle");
  function currentTheme() {
    var set = root.getAttribute("data-theme");
    if (set) { return set; }
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  if (toggle) {
    toggle.addEventListener("click", function () {
      var next = currentTheme() === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("theme", next); } catch (e) {}
    });
  }

  // ----- countdowns -----
  function parts(deadline) {
    var left = new Date(deadline).getTime() - Date.now();
    if (isNaN(left)) { return null; }
    var secs = Math.max(0, Math.floor(left / 1000));
    return {
      over: left <= 0,
      d: Math.floor(secs / 86400),
      h: Math.floor((secs % 86400) / 3600),
      m: Math.floor((secs % 3600) / 60),
      s: secs % 60
    };
  }
  function two(n) { return n < 10 ? "0" + n : String(n); }

  // Short text ("Due in 2d 5h") on cards and detail pages
  var lines = document.querySelectorAll(".countdown[data-deadline]");
  function renderLine(el) {
    var p = parts(el.getAttribute("data-deadline"));
    if (!p) { return; }
    var chip = el.closest(".chip");
    if (p.over) {
      el.textContent = "Deadline passed";
    } else if (p.d > 0) {
      el.textContent = "Due in " + p.d + "d " + p.h + "h";
    } else if (p.h > 0) {
      el.textContent = "Due in " + p.h + "h " + p.m + "m";
    } else {
      el.textContent = "Due in " + p.m + "m " + two(p.s) + "s";
    }
    if (chip) {
      chip.classList.toggle("is-over", p.over);
      chip.classList.toggle("is-soon", !p.over && p.d === 0);
    }
  }

  // Big numerals (days / hours / minutes) in the hero and detail tiles
  var clocks = document.querySelectorAll("[data-clock]");
  function renderClock(el) {
    var p = parts(el.getAttribute("data-clock"));
    if (!p) { return; }
    el.querySelector('[data-unit="d"]').textContent = p.d;
    el.querySelector('[data-unit="h"]').textContent = two(p.h);
    el.querySelector('[data-unit="m"]').textContent = two(p.m);
    el.classList.toggle("is-over", p.over);
  }

  function tick() {
    for (var i = 0; i < lines.length; i++) { renderLine(lines[i]); }
    for (var j = 0; j < clocks.length; j++) { renderClock(clocks[j]); }
  }
  if (lines.length || clocks.length) {
    tick();
    setInterval(tick, 1000);
  }

  // ----- entrance reveal: fade cards up as they come into view (CSS skips this for reduced motion) -----
  var items = document.querySelectorAll(".reveal");
  if (!("IntersectionObserver" in window)) {
    for (var k = 0; k < items.length; k++) { items[k].classList.add("is-visible"); }
    return;
  }
  var seen = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
        seen.unobserve(entry.target);
      }
    });
  }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });
  for (var n = 0; n < items.length; n++) { seen.observe(items[n]); }
})();
