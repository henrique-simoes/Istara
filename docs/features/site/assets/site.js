
(function () {
  var root = document.documentElement;
  var button = document.querySelector("[data-theme-toggle]");
  var saved = localStorage.getItem("istara-docs-theme") || "system";

  function applyTheme(theme) {
    if (theme === "system") {
      root.removeAttribute("data-theme");
    } else {
      root.setAttribute("data-theme", theme);
    }
    if (button) {
      button.textContent = "Theme: " + theme;
    }
    localStorage.setItem("istara-docs-theme", theme);
  }

  applyTheme(saved);
  if (button) {
    button.addEventListener("click", function () {
      var current = localStorage.getItem("istara-docs-theme") || "system";
      var next = current === "system" ? "light" : current === "light" ? "dark" : "system";
      applyTheme(next);
    });
  }

  var toggle = document.querySelector("[data-nav-toggle]");
  if (toggle) {
    toggle.addEventListener("click", function () {
      var open = document.body.classList.toggle("nav-open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  var search = document.getElementById("doc-search");
  if (!search) {
    return;
  }
  var items = Array.prototype.slice.call(document.querySelectorAll("[data-search-text]"));
  var sections = Array.prototype.slice.call(document.querySelectorAll("[data-nav-section]"));

  function normalize(value) {
    return (value || "").toLowerCase().trim();
  }

  search.addEventListener("input", function () {
    var query = normalize(search.value);
    items.forEach(function (item) {
      var match = !query || normalize(item.getAttribute("data-search-text")).indexOf(query) !== -1;
      item.hidden = !match;
    });
    sections.forEach(function (section) {
      var visible = Array.prototype.slice.call(section.querySelectorAll("[data-search-item]")).some(function (item) {
        return !item.hidden;
      });
      section.hidden = query && !visible;
    });
  });
})();
