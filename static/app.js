// Dark mode toggle and live deadline countdowns. No libraries.

(function () {
  // ----- dark mode -----
  var button = document.getElementById("theme-toggle");

  function currentTheme() {
    var set = document.documentElement.getAttribute("data-theme");
    if (set) { return set; }
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  if (button) {
    button.addEventListener("click", function () {
      var next = currentTheme() === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      try { localStorage.setItem("theme", next); } catch (e) {}
    });
  }

  // ----- deadline countdowns -----
  var timers = document.querySelectorAll(".countdown[data-deadline]");

  function two(n) { return n < 10 ? "0" + n : String(n); }

  function render(el) {
    var left = new Date(el.getAttribute("data-deadline")).getTime() - Date.now();
    if (isNaN(left)) { return; }
    if (left <= 0) {
      el.textContent = "Deadline passed";
      el.className = "countdown over";
      return;
    }
    var secs = Math.floor(left / 1000);
    var days = Math.floor(secs / 86400);
    var hours = Math.floor((secs % 86400) / 3600);
    var mins = Math.floor((secs % 3600) / 60);

    if (days > 0) {
      el.textContent = "Due in " + days + "d " + hours + "h";
    } else if (hours > 0) {
      el.textContent = "Due in " + hours + "h " + mins + "m";
    } else {
      el.textContent = "Due in " + mins + "m " + two(secs % 60) + "s";
    }
    el.className = days === 0 ? "countdown soon" : "countdown";
  }

  function tick() {
    for (var i = 0; i < timers.length; i++) { render(timers[i]); }
  }

  if (timers.length) {
    tick();
    setInterval(tick, 1000);
  }
})();
