#!/usr/bin/env python3
"""Static CSS and JavaScript assets for the generated feature docs site."""

from __future__ import annotations

def site_css() -> str:
    return """
:root {
  color-scheme: light;
  --logo-bg: #bdb6a4;
  --bg: #bdb6a4;
  --surface: #f7f3ea;
  --panel: #eee7da;
  --text: #18201c;
  --muted: #5f584c;
  --subtle: #ded4c2;
  --border: #cfc4ae;
  --accent: #1f6843;
  --accent-strong: #123d29;
  --accent-soft: #dfe9d7;
  --gold: #9a7730;
  --gold-soft: #efe1bf;
  --teal-soft: #d9e4df;
  --blue-soft: #dce3e7;
  --amber-soft: #eadbc0;
  --shadow: 0 12px 28px rgba(24, 32, 28, 0.12);
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --logo-bg: #26231d;
  --bg: #26231d;
  --surface: #161915;
  --panel: #20241e;
  --text: #f3f7f1;
  --muted: #b8c4bd;
  --subtle: #2e352c;
  --border: #41483e;
  --accent: #7ddc9d;
  --accent-strong: #a8efc0;
  --accent-soft: #173321;
  --gold: #f1c35a;
  --gold-soft: #332714;
  --teal-soft: #152b2e;
  --blue-soft: #162033;
  --amber-soft: #332614;
  --shadow: 0 18px 38px rgba(0, 0, 0, 0.32);
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 15px;
  line-height: 1.55;
  overflow-x: hidden;
}
a { color: var(--accent-strong); }
a:focus-visible, button:focus-visible, input:focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
}
.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}
.skip-link {
  position: fixed;
  left: 1rem;
  top: -5rem;
  z-index: 30;
  border-radius: 8px;
  background: var(--accent-strong);
  color: #fff;
  padding: 0.65rem 0.9rem;
}
.skip-link:focus { top: 1rem; }
.topbar {
  position: sticky;
  top: 0;
  z-index: 20;
  display: grid;
  grid-template-columns: minmax(15rem, 20rem) auto minmax(18rem, 1fr) auto;
  gap: 0.75rem;
  align-items: center;
  min-height: 4.1rem;
  border-bottom: 1px solid var(--border);
  background: color-mix(in srgb, var(--surface) 94%, transparent);
  backdrop-filter: blur(14px);
  padding: 0.65rem 1rem;
}
.brand {
  display: inline-flex;
  gap: 0.7rem;
  align-items: center;
  color: var(--text);
  text-decoration: none;
}
.brand-logo {
  width: 2.35rem;
  height: 2.35rem;
  object-fit: cover;
  border: 0;
  border-radius: 8px;
  background: var(--logo-bg);
  box-shadow: 0 7px 18px rgba(24, 32, 28, 0.12);
}
.brand small, .sidebar-heading span, .nav-tree small {
  display: block;
  color: var(--muted);
  font-size: 0.78rem;
}
.menu-button, .utility-nav button, .hero-actions a, .card-actions a, .audience-tabs a, .resource-grid a, .install-card button, .install-card > a {
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  color: var(--text);
  padding: 0.55rem 0.75rem;
  text-decoration: none;
}
.menu-button { display: none; }
.search-form input {
  width: 100%;
  min-height: 2.7rem;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--panel);
  color: var(--text);
  padding: 0 0.9rem;
}
.utility-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}
.utility-nav a {
  color: var(--muted);
  text-decoration: none;
}
.layout-shell {
  display: grid;
  grid-template-columns: minmax(17rem, 21rem) minmax(0, 1fr);
  min-height: calc(100vh - 4.1rem);
}
.sidebar {
  position: sticky;
  top: 4.1rem;
  align-self: start;
  height: calc(100vh - 4.1rem);
  overflow-y: auto;
  border-right: 1px solid var(--border);
  background: var(--surface);
  padding: 1rem;
}
.sidebar-heading {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: baseline;
  border-bottom: 1px solid var(--border);
  padding-bottom: 0.75rem;
  margin-bottom: 0.75rem;
}
.nav-tree h2 {
  color: var(--muted);
  font-size: 0.75rem;
  margin: 1rem 0 0.35rem;
  text-transform: uppercase;
  letter-spacing: 0;
}
.nav-tree ul {
  list-style: none;
  margin: 0;
  padding: 0;
}
.nav-tree a {
  display: block;
  border-radius: 8px;
  color: var(--text);
  padding: 0.5rem 0.55rem;
  text-decoration: none;
}
.nav-tree a:hover, .nav-tree a.active {
  background: var(--accent-soft);
  color: var(--accent-strong);
}
.content {
  min-width: 0;
  max-width: 100%;
  overflow-x: hidden;
  padding: 1.5rem;
}
.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(14rem, 18rem);
  gap: 1.25rem;
  max-width: 88rem;
  margin: 0 auto;
}
.doc-panel, .toc-panel, .metric-grid article, .group-card, .feature-card, .glossary-card, .related-panel {
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  box-shadow: var(--shadow);
}
.doc-panel {
  min-width: 0;
  padding: 1.75rem;
}
.toc-panel {
  position: sticky;
  top: 5.75rem;
  align-self: start;
  padding: 1rem;
}
.toc-panel h2 {
  margin: 0 0 0.6rem;
  border: 0;
  padding: 0;
  font-size: 0.95rem;
}
.toc-panel ul {
  list-style: none;
  margin: 0;
  padding: 0;
}
.toc-panel a {
  display: block;
  padding: 0.25rem 0;
  color: var(--muted);
  text-decoration: none;
}
.toc-level-3 { padding-left: 0.8rem; }
h1, h2, h3 { line-height: 1.2; letter-spacing: 0; }
h1 { font-size: 2.15rem; margin: 0 0 0.65rem; }
h2 { margin-top: 1.75rem; border-top: 1px solid var(--border); padding-top: 1.1rem; font-size: 1.32rem; }
h3 { font-size: 1.05rem; }
p { color: var(--text); }
.lede {
  color: var(--muted);
  font-size: 1rem;
  max-width: 62ch;
  overflow-wrap: break-word;
}
.eyebrow {
  margin: 0 0 0.35rem;
  color: var(--accent-strong);
  font-size: 0.78rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0;
}
.home-hero, .feature-hero {
  border-bottom: 1px solid var(--border);
  margin-bottom: 1.5rem;
  padding-bottom: 1.25rem;
}
.home-page .content-grid {
  grid-template-columns: minmax(0, 1fr);
  max-width: 96rem;
}
.home-page .doc-panel {
  border: 0;
  background: transparent;
  box-shadow: none;
  padding: 0;
}
.home-page .toc-panel { display: none; }
.home-hero {
  display: flex;
  max-width: 100%;
  min-height: clamp(22rem, 50vh, 30rem);
  flex-direction: column;
  justify-content: flex-end;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 14px;
  background:
    linear-gradient(90deg, color-mix(in srgb, var(--logo-bg) 100%, transparent) 0%, color-mix(in srgb, var(--logo-bg) 96%, transparent) 43%, color-mix(in srgb, var(--logo-bg) 46%, transparent) 100%),
    url("istara-logo.png") right 8% center / min(39vw, 28rem) auto no-repeat,
    var(--logo-bg);
  padding: clamp(1.5rem, 5vw, 4rem);
}
.hero-copy {
  width: min(45rem, 100%);
  max-width: 100%;
  min-width: 0;
}
.home-hero h1 {
  font-size: clamp(3rem, 6vw, 4.9rem);
  margin-bottom: 0.35rem;
  letter-spacing: 0;
}
.hero-actions, .card-actions, .audience-tabs, .link-cluster, .resource-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  align-items: center;
}
.hero-actions a:first-child, .audience-tabs a[aria-current="page"], .install-card.primary button {
  background: var(--accent-strong);
  color: #fff;
  border-color: var(--accent-strong);
}
.hero-actions a:nth-child(3) {
  background: var(--gold-soft);
  border-color: color-mix(in srgb, var(--gold) 50%, var(--border));
}
.install-section {
  margin-top: 1.35rem;
}
.install-grid {
  display: grid;
  grid-template-columns: 1.1fr 1.1fr 0.9fr;
  gap: 0.85rem;
}
.install-card {
  min-width: 0;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface);
  box-shadow: var(--shadow);
  padding: 1rem;
}
.install-card.primary {
  border-color: color-mix(in srgb, var(--accent) 55%, var(--border));
  background: linear-gradient(180deg, var(--surface), var(--accent-soft));
}
.install-card h3 {
  margin: 0.15rem 0 0.45rem;
  font-size: 1.05rem;
}
.install-card pre {
  max-width: 100%;
  overflow: hidden;
  margin: 1rem 0 0.8rem;
}
.install-card code {
  white-space: pre;
}
.metric-grid, .group-grid, .glossary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.85rem;
}
.metric-grid article, .group-card, .glossary-card {
  padding: 0.95rem;
}
.metric-grid strong {
  display: block;
  font-size: 1.65rem;
  line-height: 1;
}
.metric-grid span, .path-line, .concept-line {
  color: var(--muted);
}
.section-block { margin-top: 2rem; }
.section-heading {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: end;
  margin-bottom: 1rem;
}
.section-heading h2 {
  border: 0;
  margin: 0;
  padding: 0;
}
.section-heading p { margin: 0; color: var(--muted); }
.feature-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.85rem;
}
.feature-card {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem;
}
.feature-card h2, .group-card h2, .glossary-card h2 {
  border: 0;
  margin: 0.1rem 0 0.4rem;
  padding: 0;
  font-size: 1.05rem;
}
.feature-title-row {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: start;
}
.status-chip {
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--amber-soft);
  color: var(--text);
  padding: 0.35rem 0.7rem;
  white-space: nowrap;
}
.breadcrumbs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  color: var(--muted);
  margin-bottom: 1rem;
}
.breadcrumbs span::before {
  content: "/";
  margin-right: 0.45rem;
  color: var(--muted);
}
.meta-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.75rem;
  margin: 1rem 0;
}
.meta-grid div {
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--panel);
  padding: 0.8rem;
}
.meta-grid dt {
  color: var(--muted);
  font-size: 0.78rem;
}
.meta-grid dd {
  margin: 0.2rem 0 0;
}
.link-cluster a, .link-cluster span {
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--blue-soft);
  padding: 0.35rem 0.65rem;
  text-decoration: none;
}
code {
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--subtle);
  padding: 0.1rem 0.3rem;
  word-break: break-word;
}
pre code {
  display: block;
  overflow-x: auto;
  padding: 1rem;
}
[hidden] { display: none !important; }
@media (max-width: 1180px) {
  .topbar { grid-template-columns: 1fr auto; }
  .search-form { grid-column: 1 / -1; }
  .utility-nav { justify-content: flex-end; }
  .content-grid { grid-template-columns: 1fr; }
  .toc-panel { position: static; }
  .metric-grid, .group-grid, .install-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .home-hero { background-size: min(48vw, 24rem) auto; }
}
@media (max-width: 820px) {
  .topbar {
    grid-template-columns: 1fr;
    align-items: stretch;
  }
  .search-form { grid-column: auto; }
  .utility-nav {
    justify-content: flex-start;
    overflow-x: auto;
    padding-bottom: 0.2rem;
  }
  .menu-button { display: inline-flex; }
  .layout-shell { grid-template-columns: 1fr; }
  .sidebar {
    display: none;
    position: static;
    height: auto;
    max-height: 65vh;
    border-right: 0;
    border-bottom: 1px solid var(--border);
  }
  body.nav-open .sidebar { display: block; }
  .content { padding: 1rem; }
  .doc-panel { padding: 1.2rem; }
  .feature-list, .metric-grid, .group-grid, .glossary-grid, .meta-grid, .install-grid { grid-template-columns: 1fr; }
  .feature-card, .feature-title-row, .section-heading { display: block; }
  h1 { font-size: 2rem; }
  .home-hero {
    width: 100%;
    max-width: calc(100vw - 2rem);
    min-height: 29rem;
    background:
      linear-gradient(180deg, color-mix(in srgb, var(--logo-bg) 82%, transparent) 0%, var(--logo-bg) 100%),
      url("istara-logo.png") center 1rem / min(72vw, 17rem) auto no-repeat,
      var(--logo-bg);
    padding-top: 13rem;
  }
  .hero-copy, .lede, .hero-actions { max-width: 20rem; }
  .hero-actions a {
    flex: 1 1 9rem;
    text-align: center;
  }
  .home-hero h1 { font-size: clamp(2.85rem, 15vw, 4rem); }
}
@media (max-width: 480px) {
  .hero-copy, .lede, .hero-actions { max-width: 18.5rem; }
}
"""


def site_js() -> str:
    return """
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

  Array.prototype.slice.call(document.querySelectorAll("[data-copy-command]")).forEach(function (copyButton) {
    copyButton.addEventListener("click", function () {
      var command = copyButton.getAttribute("data-copy-command") || "";
      if (!command || !navigator.clipboard) {
        return;
      }
      navigator.clipboard.writeText(command).then(function () {
        copyButton.textContent = "Copied";
        window.setTimeout(function () {
          copyButton.textContent = "Copy command";
        }, 1800);
      });
    });
  });
})();
"""
