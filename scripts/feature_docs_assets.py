#!/usr/bin/env python3
"""Static CSS and JavaScript assets for the generated feature docs site."""

from __future__ import annotations


def site_css() -> str:
    return """
:root {
  color-scheme: light;
  --logo-bg: #dcd9ce;
  --bg: #f8f2e6;
  --surface: #ffffff;
  --surface-main: #f8f2e6;
  --panel: #f6f3f2;
  --text: #1b1b1b;
  --muted: #6b6b5f;
  --subtle: #e5e2e1;
  --border: #dcd9ce;
  --accent: #456644;
  --accent-strong: #18381a;
  --accent-soft: #e2e0d1;
  --action-bg: #2f4f2f;
  --action-text: #ffffff;
  --action-soft: #f0eded;
  --gold: #8b6f29;
  --gold-soft: #e5e2e1;
  --teal-soft: #eef3ec;
  --blue-soft: #f0eded;
  --amber-soft: #e6e2d7;
  --shadow: 0 1px 0 rgba(27, 27, 27, 0.04);
  --shadow-hover: 0 14px 32px rgba(47, 79, 47, 0.1);
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --logo-bg: #313030;
  --bg: #1b1b1b;
  --surface: #252524;
  --surface-main: #1f211e;
  --panel: #313030;
  --text: #f3f0ef;
  --muted: #c9c6bc;
  --subtle: #424840;
  --border: #565b52;
  --accent: #abd0a6;
  --accent-strong: #c7edc1;
  --accent-soft: #2f4f2f;
  --action-bg: #c7edc1;
  --action-text: #022107;
  --action-soft: #32322a;
  --gold: #e2c16a;
  --gold-soft: #383527;
  --teal-soft: #26362d;
  --blue-soft: #303432;
  --amber-soft: #38362b;
  --shadow: 0 1px 0 rgba(0, 0, 0, 0.25);
  --shadow-hover: 0 14px 32px rgba(0, 0, 0, 0.32);
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 16px;
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
  border-radius: 4px;
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
  background: color-mix(in srgb, var(--bg) 94%, transparent);
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
  border-radius: 4px;
  background: var(--logo-bg);
  box-shadow: 0 1px 0 rgba(27, 27, 27, 0.08);
}
.brand small, .sidebar-heading span, .nav-tree small {
  display: block;
  color: var(--muted);
  font-size: 0.78rem;
}
.menu-button, .utility-nav button, .hero-actions a, .card-actions a, .audience-tabs a, .resource-grid a, .install-card button, .install-card > a {
  border: 1px solid var(--border);
  border-radius: 4px;
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
  border-radius: 4px;
  background: var(--surface);
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
.utility-nav a:first-child {
  border: 1px solid var(--action-bg);
  border-radius: 4px;
  background: var(--action-bg);
  color: var(--action-text);
  padding: 0.45rem 0.7rem;
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
  background: var(--surface-main);
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
  border-radius: 4px;
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
.feature-hero {
  border-bottom: 1px solid var(--border);
  margin-bottom: 1.5rem;
  padding-bottom: 1.25rem;
}
.home-page .content-grid {
  grid-template-columns: minmax(0, 1fr);
  max-width: 88rem;
}
.home-page .doc-panel {
  border: 0;
  background: transparent;
  box-shadow: none;
  padding: 0;
}
.home-page .toc-panel { display: none; }
.home-hero-v2 {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(18rem, 1.15fr);
  gap: clamp(1.25rem, 3vw, 2rem);
  align-items: stretch;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: color-mix(in srgb, var(--surface-main) 78%, var(--accent-soft));
  padding: clamp(1.25rem, 4vw, 2.4rem);
}
.hero-v2-copy {
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-width: 0;
}
.home-hero-v2 h1 {
  max-width: 17ch;
  margin: 0 0 0.9rem;
  font-size: 2.75rem;
  line-height: 1.08;
  letter-spacing: 0;
}
.hero-lede {
  max-width: 48rem;
  margin: 0;
  color: var(--muted);
  font-size: 1.02rem;
  line-height: 1.55;
}
.hero-v2-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  margin-top: 1.35rem;
}
.hero-v2-actions a {
  display: inline-flex;
  min-height: 2.55rem;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--surface);
  color: var(--text);
  padding: 0.58rem 0.78rem;
  text-decoration: none;
  font-weight: 700;
}
.hero-v2-actions a.primary-action {
  border-color: var(--action-bg);
  background: var(--action-bg);
  color: var(--action-text);
}
.hero-command-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0.75rem;
  align-items: center;
  max-width: 100%;
  margin-top: 1rem;
  border: 1px solid color-mix(in srgb, var(--accent) 34%, var(--border));
  border-radius: 4px;
  background: var(--surface);
  box-shadow: var(--shadow);
  padding: 0.75rem;
}
.hero-command-card span {
  display: block;
  color: var(--muted);
  font-size: 0.76rem;
  font-weight: 700;
  text-transform: uppercase;
}
.hero-command-card code {
  display: block;
  overflow-wrap: anywhere;
  border: 0;
  background: transparent;
  padding: 0;
  white-space: normal;
}
.hero-command-card button {
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--action-bg);
  color: var(--action-text);
  cursor: pointer;
  min-height: 2.5rem;
  padding: 0.55rem 0.7rem;
}
.hero-proof-list {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.65rem;
  margin: 1rem 0 0;
  padding: 0;
  list-style: none;
}
.hero-proof-list li {
  min-width: 0;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  padding: 0.75rem;
}
.hero-proof-list strong {
  display: block;
  font-size: 0.9rem;
}
.hero-proof-list span {
  display: block;
  margin-top: 0.18rem;
  color: var(--muted);
  font-size: 0.86rem;
}
.hero-v2-product {
  position: relative;
  min-height: 25rem;
  overflow: hidden;
}
.hero-screen {
  position: absolute;
  margin: 0;
  overflow: hidden;
  border: 1px solid color-mix(in srgb, var(--text) 14%, var(--border));
  border-radius: 8px;
  background: #070b14;
  box-shadow: 0 18px 46px rgba(27, 27, 27, 0.18);
}
:root[data-theme="dark"] .hero-screen {
  box-shadow: 0 20px 52px rgba(0, 0, 0, 0.42);
}
.hero-screen img {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 10;
  object-fit: cover;
  object-position: left top;
}
.hero-screen figcaption {
  border-top: 1px solid rgba(255, 255, 255, 0.12);
  color: #f3f0ef;
  font-size: 0.82rem;
  padding: 0.6rem 0.75rem;
}
.hero-screen-main {
  top: 0.25rem;
  right: 0;
  width: min(94%, 38rem);
}
.hero-screen-task {
  bottom: 1.5rem;
  left: 0;
  width: min(52%, 20rem);
}
.hero-screen-skills {
  right: 2.5rem;
  bottom: 0.15rem;
  width: min(46%, 18rem);
}
.hero-actions, .card-actions, .audience-tabs, .link-cluster, .resource-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  align-items: center;
}
.hero-actions a:first-child, .audience-tabs a[aria-current="page"], .install-card.primary button {
  background: var(--action-bg);
  color: var(--action-text);
  border-color: var(--action-bg);
}
.hero-actions a:nth-child(3) {
  background: var(--surface);
  border-color: var(--border);
}
.install-section-v2 {
  margin-top: 2rem;
}
.install-grid {
  display: grid;
  grid-template-columns: 1.1fr 1.1fr 0.9fr;
  gap: 1.5rem;
}
.install-card {
  min-width: 0;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  box-shadow: var(--shadow);
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
.install-card:hover, .tour-card:hover, .feature-cluster-grid article:hover {
  box-shadow: var(--shadow-hover);
}
.install-card.primary {
  border-color: color-mix(in srgb, var(--accent) 55%, var(--border));
  background: color-mix(in srgb, var(--surface) 72%, var(--accent-soft));
}
.install-card h3 {
  margin: 0.15rem 0 0.45rem;
  font-size: 1.05rem;
}
.install-card pre {
  max-width: 100%;
  overflow-x: auto;
  margin: 1rem 0 0.8rem;
}
.install-card code {
  white-space: pre;
}
.product-tour-v2 {
  overflow: hidden;
}
.product-tour-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1rem;
}
.tour-card {
  min-width: 0;
  margin: 0;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  box-shadow: var(--shadow);
}
.tour-card img {
  display: block;
  width: 100%;
  aspect-ratio: 4 / 3;
  object-fit: cover;
  object-position: left top;
  border-bottom: 1px solid var(--border);
  background: #080b14;
}
.tour-card figcaption {
  display: grid;
  gap: 0.25rem;
  padding: 0.85rem;
}
.tour-card strong {
  font-size: 0.98rem;
}
.tour-card span {
  color: var(--muted);
  font-size: 0.9rem;
}
.feature-cluster-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1rem;
}
.feature-cluster-grid article {
  min-width: 0;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  box-shadow: var(--shadow);
  padding: 1rem;
}
.feature-cluster-grid span, .research-flow-rail li span {
  display: inline-flex;
  min-width: 2rem;
  color: var(--accent-strong);
  font-weight: 800;
}
.feature-cluster-grid h3 {
  margin: 0.5rem 0 0.35rem;
}
.feature-cluster-grid p {
  margin: 0;
  color: var(--muted);
}
.research-flow-section {
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
  gap: 1rem;
  align-items: start;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--panel);
  padding: clamp(1rem, 3vw, 1.5rem);
}
.research-flow-section h2 {
  border: 0;
  margin: 0;
  padding: 0;
}
.research-flow-rail {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.65rem;
  margin: 0;
  padding: 0;
  list-style: none;
}
.research-flow-rail li {
  min-width: 0;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  padding: 0.8rem;
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
  border-radius: 4px;
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
  border-radius: 4px;
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
  .metric-grid, .group-grid, .install-grid, .product-tour-grid, .feature-cluster-grid, .bento-grid, .technical-grid, .skills-categories-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .home-hero-v2 {
    grid-template-columns: 1fr;
  }
  .hero-v2-product {
    min-height: 29rem;
  }
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
  .feature-list, .metric-grid, .group-grid, .glossary-grid, .meta-grid, .install-grid, .product-tour-grid, .feature-cluster-grid, .research-flow-section, .research-flow-rail, .bento-grid, .technical-grid, .skills-categories-grid { grid-template-columns: 1fr; }
  .bento-card.span-2, .skill-cat-card.full-row { grid-column: span 1 !important; }
  .feature-card, .feature-title-row, .section-heading { display: block; }
  h1 { font-size: 2rem; }
  .home-hero-v2 {
    width: 100%;
    max-width: calc(100vw - 2rem);
    min-height: auto;
    padding: 1.25rem;
  }
  .home-hero-v2 h1 {
    max-width: 100%;
    font-size: 2.35rem;
  }
  .hero-v2-product {
    min-height: auto;
  }
  .hero-screen {
    position: static;
    width: 100%;
    margin-top: 0.85rem;
  }
  .hero-screen-task, .hero-screen-skills {
    display: none;
  }
  .hero-proof-list, .hero-command-card {
    display: grid;
    grid-template-columns: 1fr;
  }
  .hero-v2-actions a {
    flex: 1 1 9rem;
    text-align: center;
  }
  .hero-command-card button {
    width: 100%;
  }
}
@media (max-width: 480px) {
  .content { padding: 0.75rem; }
  .home-hero-v2 { max-width: calc(100vw - 1.5rem); }
}

/* Premium Redesign Custom Classes */
.home-page .sidebar { display: none !important; }
.home-page .layout-shell { grid-template-columns: 1fr !important; }
.home-page .content { padding: 2rem clamp(1rem, 5vw, 3rem); }
.hero-v2-product { display: flex; flex-direction: column; gap: 1.5rem; justify-content: center; align-items: stretch; }
.hero-presentation-gif { width: 100%; height: auto; border-radius: 8px; border: 1px solid var(--border); box-shadow: 0 10px 30px rgba(0, 0, 0, 0.06); display: block; }
:root[data-theme="dark"] .hero-presentation-gif { box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35); }
.terminal-mockup { background: #161b22; border-radius: 8px; border: 1px solid #30363d; overflow: hidden; font-family: ui-monospace, SFMono-Regular, SF Mono, Menlo, Consolas, Liberation Mono, monospace; font-size: 0.82rem; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5); }
.terminal-header { background: #21262d; padding: 0.4rem 0.8rem; display: flex; align-items: center; gap: 0.35rem; border-bottom: 1px solid #30363d; }
.terminal-header .btn { width: 9px; height: 9px; border-radius: 50%; display: inline-block; }
.terminal-header .btn.close { background: #ff5f56; }
.terminal-header .btn.minimize { background: #ffbd2e; }
.terminal-header .btn.expand { background: #27c93f; }
.terminal-header .terminal-title { margin-left: auto; margin-right: auto; color: #8b949e; font-size: 0.72rem; }
.terminal-body { padding: 0.8rem; color: #c9d1d9; display: flex; flex-direction: column; gap: 0.25rem; text-align: left; }
.terminal-body .line { line-height: 1.35; }
.terminal-body .prompt { color: #58a6ff; font-weight: bold; }
.terminal-body .success { color: #56e39f; }
.terminal-body .info { color: #84c0c6; }
.spine-visual { display: flex; align-items: center; justify-content: space-between; padding: 0.5rem 0; }
.spine-visual .node { display: flex; flex-direction: column; align-items: center; gap: 0.35rem; text-align: center; min-width: 4.5rem; }
.spine-visual .dot { width: 10px; height: 10px; border-radius: 50%; background: var(--bg); border: 2px solid var(--border); box-shadow: 0 0 0 1px var(--bg); }
.spine-visual .node.active .dot { background: var(--accent); border-color: var(--accent-strong); box-shadow: 0 0 0 2px var(--bg), 0 0 8px var(--accent); }
.spine-visual .label { font-size: 0.65rem; color: var(--muted); font-weight: bold; }
.spine-visual .node.active .label { color: var(--accent-strong); }
.spine-visual .connector { flex: 1; height: 2px; background: var(--border); margin: 0 0.25rem; margin-bottom: 0.9rem; }
.bento-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1.25rem; margin-top: 1.5rem; }
a.tech-link-card { text-decoration: none; color: inherit; display: block; cursor: pointer; }
.bento-card { border: 1px solid var(--border); border-radius: 12px; background: var(--surface); padding: 1.5rem; position: relative; display: flex; flex-direction: column; gap: 0.75rem; transition: transform 0.35s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.35s ease, box-shadow 0.35s ease; box-shadow: var(--shadow); }
.bento-card:hover { transform: translateY(-4px) scale(1.03); box-shadow: var(--shadow-hover); border-color: var(--accent); z-index: 10; }
.bento-card.span-2 { grid-column: span 2; }
.bento-card.highlight { background: color-mix(in srgb, var(--surface) 92%, var(--accent-soft)); border-color: color-mix(in srgb, var(--accent) 45%, var(--border)); }
.bento-icon { font-size: 2rem; }
.bento-card h3 { margin: 0; font-size: 1.2rem; color: var(--text); }
.bento-card p { margin: 0; color: var(--muted); font-size: 0.92rem; line-height: 1.5; }
.badge { align-self: start; margin-top: auto; font-size: 0.7rem; font-weight: 700; padding: 0.25rem 0.6rem; border-radius: 99px; background: var(--accent-soft); color: var(--accent-strong); text-transform: uppercase; }

/* Technical architecture grid and tech-card upgrades */
.technical-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1.25rem; margin-top: 1.5rem; }
.tech-card { border: 1px solid var(--border); border-radius: 10px; background: var(--surface); padding: 1.25rem; display: flex; flex-direction: column; gap: 0.75rem; box-shadow: var(--shadow); transition: transform 0.35s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.35s ease, box-shadow 0.35s ease; }
.tech-card:hover { transform: translateY(-4px) scale(1.03); box-shadow: var(--shadow-hover); border-color: var(--accent); z-index: 10; }
.tech-hdr { display: flex; flex-direction: column; gap: 0.25rem; }
.tech-tag { font-size: 0.7rem; font-weight: 700; color: var(--accent); text-transform: uppercase; letter-spacing: 0.05em; }
.tech-card h3 { margin: 0; font-size: 1.08rem; color: var(--text); }
.tech-card p { margin: 0; color: var(--muted); font-size: 0.88rem; line-height: 1.45; }

/* Expanded description hover reveal */
.bento-card .expanded-desc, .tech-card .expanded-desc { max-height: 0; opacity: 0; overflow: hidden; transition: max-height 0.35s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.35s ease, margin-top 0.35s ease; margin-top: 0; font-size: 0.86rem; color: var(--muted); }
.bento-card:hover .expanded-desc, .tech-card:hover .expanded-desc { max-height: 120px; opacity: 1; margin-top: 0.5rem; }

/* Schematic image hover reveal */
.bento-card .card-tech-img, .tech-card .card-tech-img { max-height: 0; opacity: 0; overflow: hidden; transition: max-height 0.35s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.35s ease, margin-top 0.35s ease, transform 0.35s ease; margin-top: 0; transform: translateY(12px); text-align: center; border-radius: 6px; background: var(--surface); border: 1px solid var(--border); }
.bento-card .card-tech-img img, .tech-card .card-tech-img img { max-height: 140px; width: auto; max-width: 100%; object-fit: contain; vertical-align: middle; padding: 0.3rem; }
.bento-card:hover .card-tech-img, .tech-card:hover .card-tech-img { max-height: 160px; opacity: 1; margin-top: 0.75rem; transform: translateY(0); }

/* Technology detail subpages layout */
.tech-detail-layout { display: grid; grid-template-columns: 1.1fr 0.9fr; gap: 2.5rem; margin-top: 1.5rem; }
.tech-detail-copy { display: flex; flex-direction: column; gap: 1.25rem; }
.tech-detail-visual { position: sticky; top: 5.5rem; align-self: start; border: 1px solid var(--border); border-radius: 12px; background: var(--surface); box-shadow: var(--shadow); padding: 1rem; }
.tech-detail-visual img { width: 100%; height: auto; border-radius: 6px; display: block; background: #f8f2e6; }
.tech-detail-back { display: inline-flex; align-items: center; gap: 0.5rem; margin-bottom: 1.5rem; font-size: 0.9rem; color: var(--muted); text-decoration: none; font-weight: 500; transition: color 0.2s ease; }
.tech-detail-back:hover { color: var(--accent-strong); }
.tech-detail-back::before { content: "←"; font-size: 1.1rem; }
.code-refs-box { margin-top: 1.5rem; padding: 1rem; border-radius: 8px; background: var(--panel); border: 1px solid var(--border); }
.code-refs-box h4 { margin: 0 0 0.5rem 0; font-size: 0.95rem; color: var(--text); font-weight: 600; }
.code-refs-box ul { margin: 0; padding-left: 1.2rem; color: var(--muted); font-size: 0.86rem; }
.code-refs-box li { margin-bottom: 0.25rem; }

/* Alternating Technology Sections for Homepage */
.tech-sections-container {
  display: flex;
  flex-direction: column;
  margin-top: 2rem;
}
.tech-section-row {
  display: flex;
  align-items: center;
  gap: 5rem;
  padding: 6rem 0;
  border-bottom: 1px solid var(--border);
  position: relative;
}
.tech-section-row:last-child {
  border-bottom: none;
  padding-bottom: 0;
}
.tech-section-row:nth-child(even) {
  flex-direction: row-reverse;
}
.tech-section-copy {
  flex: 1.1;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  align-items: flex-start;
  text-align: left;
}
.tech-section-num {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--muted);
  font-family: monospace;
}
.tech-section-tag {
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.tech-section-copy h3 {
  margin: 0;
  font-size: 2rem;
  line-height: 1.25;
  color: var(--text);
  font-weight: 700;
}
.tech-section-desc {
  margin: 0;
  font-size: 1.1rem;
  color: var(--text);
  line-height: 1.5;
}
.tech-section-detail {
  margin: 0;
  font-size: 0.95rem;
  color: var(--muted);
  line-height: 1.5;
}
.tech-section-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--surface);
  color: var(--text);
  padding: 0.6rem 1.1rem;
  font-size: 0.9rem;
  text-decoration: none;
  font-weight: 500;
  transition: all 0.25s ease;
  margin-top: 0.5rem;
}
.tech-section-btn:hover {
  background: var(--accent-soft);
  color: var(--accent-strong);
  border-color: var(--accent);
}
.tech-section-visual {
  flex: 0.9;
  text-align: center;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 0.5rem;
  background: transparent;
}
.tech-section-visual img {
  max-width: 100%;
  height: auto;
  max-height: 380px;
  object-fit: contain;
  display: block;
  border: 2px solid var(--accent);
  border-radius: 8px;
  background: var(--surface);
  padding: 0.5rem;
}

@media (max-width: 960px) {
  .tech-detail-layout { grid-template-columns: 1fr; gap: 1.5rem; }
  .tech-detail-visual { position: static; }
  .tech-section-row, .tech-section-row:nth-child(even) {
    flex-direction: column !important;
    gap: 2.5rem;
    padding: 4rem 0;
  }
  .tech-section-copy {
    width: 100%;
  }
  .tech-section-visual {
    width: 100%;
  }
  .tech-section-visual img {
    max-height: 280px;
  }
}

.skills-categories-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 1.25rem; margin-top: 1.5rem; }
.skill-cat-card { border: 1px solid var(--border); border-radius: 10px; background: var(--surface); padding: 1.25rem; display: flex; flex-direction: column; gap: 0.75rem; box-shadow: var(--shadow); text-align: left; }
.skill-cat-card h4 { margin: 0; font-size: 1.05rem; color: var(--text); }
.skills-count { font-size: 0.72rem; font-weight: 700; color: var(--muted); text-transform: uppercase; }
.skill-cat-card ul { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 0.45rem; }
.skill-cat-card li { font-size: 0.86rem; color: var(--text); padding-left: 0.75rem; position: relative; }
.skill-cat-card li::before { content: "•"; color: var(--accent); position: absolute; left: 0; font-weight: bold; }
.skill-cat-card.full-row { grid-column: 1 / -1; background: var(--panel); }
.skills-list-inline { display: flex; flex-wrap: wrap; gap: 0.75rem; }
.skills-list-inline span { background: var(--surface); border: 1px solid var(--border); border-radius: 6px; padding: 0.35rem 0.75rem; font-size: 0.86rem; font-weight: 500; color: var(--text); }
.docs-hub-page .feature-hero { border-bottom: 1px solid var(--border); margin-bottom: 1.5rem; padding-bottom: 1.25rem; }
.docs-hub-page .content { padding: 1.5rem; }

/* Premium Scroll Reveal Animations & Keyframes */
.bento-card, .tech-card, .skill-cat-card, .research-flow-rail li, .tech-section-row { transition: opacity 0.65s cubic-bezier(0.16, 1, 0.3, 1), transform 0.65s cubic-bezier(0.16, 1, 0.3, 1); }
@media (prefers-reduced-motion: no-preference) {
  .scroll-animate { opacity: 0.05; transform: translateY(24px) scale(0.97); }
  .scroll-animate.visible { opacity: 1; transform: translateY(0) scale(1); }
  @supports ((animation-timeline: view()) and (animation-range: entry)) {
    @keyframes fade-in-up {
      from { opacity: 0.1; transform: translateY(30px) scale(0.96); }
      to { opacity: 1; transform: translateY(0) scale(1); }
    }
    .bento-card, .tech-card, .skill-cat-card, .research-flow-rail li, .tech-section-row { animation: fade-in-up auto linear both; animation-timeline: view(); animation-range: entry 5% entry 40%; }
  }
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

  // Scroll reveal IntersectionObserver fallback for older or non-webkit browsers
  if (!CSS.supports('(animation-timeline: view()) and (animation-range: entry)')) {
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
          }
        });
      },
      {
        threshold: 0.08
      }
    );

    var cards = document.querySelectorAll('.bento-card, .tech-card, .skill-cat-card, .research-flow-rail li, .tech-section-row');
    cards.forEach(function (card) {
      card.classList.add('scroll-animate');
      observer.observe(card);
    });
  }
})();
"""
