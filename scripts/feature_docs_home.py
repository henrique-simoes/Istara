#!/usr/bin/env python3
"""Homepage sections and assets for the generated feature docs site."""

from __future__ import annotations

import html
import shutil
from pathlib import Path

HOME_SCREENSHOTS = (
    ("Screenshots/Screenshot 2026-04-02 at 16.37.30.png", "home-chat.png"),
    ("Screenshots/Screenshot 2026-04-02 at 16.38.47.png", "home-tasks.png"),
    ("Screenshots/Screenshot 2026-04-02 at 16.39.11.png", "home-skills.png"),
    ("Screenshots/Screenshot 2026-04-02 at 16.39.28.png", "home-interfaces.png"),
    ("Screenshots/istara_presentation.gif", "istara_presentation.gif"),
)

PRIMARY_INSTALL = "brew install --cask henrique-simoes/istara/istara"
SHELL_INSTALL = "curl -fsSL https://raw.githubusercontent.com/henrique-simoes/Istara/main/scripts/install-istara.sh | bash"
SOURCE_INSTALL = "git clone https://github.com/henrique-simoes/Istara.git"

HERO_PROOFS = (
    ("Local-first Security", "Run workspace inference and model routing entirely on your own local machine."),
    ("Evidence-gated Rigor", "Keep report materials tied to source spans, inter-coder review, and reconciled tasks."),
    ("Compute Swarm Pool", "Use project-authorized local models and donated hardware compute with route evidence."),
)

def copy_home_screenshots(root: Path, assets: Path) -> list[Path]:
    written: list[Path] = []
    for source_rel, target_name in HOME_SCREENSHOTS:
        source = root / source_rel
        if source.exists():
            target = assets / target_name
            shutil.copyfile(source, target)
            written.append(target)
    return written

def _copy_button(command: str, label: str = "Copy command") -> str:
    escaped = html.escape(command)
    return f'<button type="button" data-copy-command="{escaped}">{html.escape(label)}</button>'

def _install_card(kind: str, title: str, body: str, command: str, *, primary: bool = False) -> str:
    css_class = "install-card primary" if primary else "install-card"
    return (
        f'<article class="{css_class}">'
        f'<p class="eyebrow">{html.escape(kind)}</p>'
        f"<h3>{html.escape(title)}</h3>"
        f"<p>{html.escape(body)}</p>"
        f"<pre><code>{html.escape(command)}</code></pre>"
        f"{_copy_button(command)}"
        "</article>"
    )

def _tech_section(num: str, tag: str, title: str, desc: str, detail: str, img: str, link: str) -> str:
    return f"""
<div class="tech-section-row scroll-animate">
  <div class="tech-section-copy">
    <span class="tech-section-num">{html.escape(num)}</span>
    <span class="tech-section-tag">{html.escape(tag)}</span>
    <h3>{html.escape(title)}</h3>
    <p class="tech-section-desc">{html.escape(desc)}</p>
    <p class="tech-section-detail">{html.escape(detail)}</p>
    <a href="{html.escape(link)}" class="tech-section-btn">Explore Architecture Deep-Dive →</a>
  </div>
  <div class="tech-section-visual">
    <img src="{html.escape(img)}" alt="{html.escape(title)} Schematic" loading="lazy">
  </div>
</div>
"""

def home_marketing_sections() -> str:
    proofs_html = "".join(
        f"<li><strong>{html.escape(title)}</strong><span>{html.escape(copy)}</span></li>"
        for title, copy in HERO_PROOFS
    )
    
    swarm_sections_html = "".join([
        _tech_section(
            "01 / 10", "Spine Guarded", "Intelligent Grounded Chat",
            "Ask research questions without losing grounding. Project chat keeps source material, accepted evidence, and task context close to the conversation for fully reviewable evidence.",
            "Istara's source-bounded reasoning and context DAG routing ensure that every AI claim is completely backed by source citations. Powered by semantic vector search.",
            "assets/tech_chat.png", "technology/grounded-chat.html"
        ),
        _tech_section(
            "02 / 10", "Double Diamond", "53+ UX Research Skills",
            "Run focused UX research skills from competitive analysis, card sorting, and accessibility audits to SUS usability scoring and design briefs.",
            "Workflows are organized across Discover, Define, Develop, and Deliver phases of the Double Diamond. The execution harness supports custom skill creation and automatic prompt-evolution.",
            "assets/tech_skills.png", "technology/ux-skills.html"
        ),
        _tech_section(
            "03 / 10", "Governed Prompts", "Self-Evolving Agents & Personas",
            "Evolve Cleo, Sentinel, Pixel, Sage, and Echo from project-scoped process memory and verified outcomes. Create new agents at runtime via Memento agent factory.",
            "The runtime Memento agent factory reads from project-scoped ReasoningBank memory stores, allowing agents to evolve their prompts and strategies governed by security contracts.",
            "assets/tech_swarm.png", "technology/evolving-agents.html"
        ),
        _tech_section(
            "04 / 10", "Local Swarms", "Collaborative Compute Swarm",
            "Share GPU and CPU capacity with team members via a WebSocket-based Compute Relay. Route inference requests to local nodes with capability detection and automatic failover.",
            "Idle hardware forms a secure WebSocket-based compute relay pool. Requests are dynamically routed to local donor nodes with automatic fallback queue management.",
            "assets/tech_relay.png", "technology/compute-swarm.html"
        ),
    ])

    arch_sections_html = "".join([
        _tech_section(
            "05 / 10", "Retrieval", "Hybrid RAG + Graph RAG",
            "Get exact evidence with Hybrid RAG (LanceDB vector + BM25 keyword search blended via Reciprocal Rank Fusion) and explore relationships across sources, codes, and tasks via Graph RAG.",
            "Graph answers must backfill exact evidence before promotion. Hybrid rank blending prevents semantic drift and ensures precise reference lookup across multi-thousand-page repositories.",
            "assets/tech_rag.png", "technology/hybrid-rag.html"
        ),
        _tech_section(
            "06 / 10", "Verification", "Multi-Model Ensemble Health",
            "Independent atomic extraction and open coding reduce bias. Distinct project-authorized models independently code same evidence units with Fleiss' Kappa reliability before human reconciliation.",
            "Real-time inter-coder consensus metrics score reliability across models, automatically flagging diverging classifications for human adjudication before promotion.",
            "assets/tech_reliability.png", "technology/multi-model.html"
        ),
        _tech_section(
            "07 / 10", "Collaboration", "Distributed Compute & Roles",
            "Idle hardware forms a collaborative compute swarm. Strict separation of access roles (Admin/Researcher) ensures secure operation, protected by WebAuthn passkeys and Fernet field encryption.",
            "Cryptographic passkeys and field-level AES encryption prevent data leaks, keeping active local SQLite workspaces completely isolated and secure.",
            "assets/tech_roles.png", "technology/distributed-compute.html"
        ),
        _tech_section(
            "08 / 10", "Governance", "Human-in-the-Loop Kanban",
            "Agents pick up tasks and propose findings, but they remain provisional and in review. Human-in-the-loop review states and reconciliation ensure only accepted findings enter approved Done tasks.",
            "The human researcher retains absolute control. Task-level review gates prevent automated findings from leaking into reports without researcher sign-off.",
            "assets/tech_kanban.png", "technology/human-kanban.html"
        ),
        _tech_section(
            "09 / 10", "Design Handoff", "Stitch & Figma Interfaces",
            "Import Figma files to link screen design decisions to accepted research evidence. Use the Google Stitch MCP server to generate wireframes and specs directly from reportable insights.",
            "Bidirectional canvas syncing connects design layout layers to qualitative research nuggets. Enables evidence-backed design handoffs that developers can trace immediately.",
            "assets/tech_handoff.png", "technology/stitch-figma.html"
        ),
        _tech_section(
            "10 / 10", "Reporting", "Grounded Decisions & Reports",
            "Export research reports directly from approved Done tasks. Ground every recommendation back through the spine: accepted atoms → facts → insights → recommendations linked to raw source spans.",
            "Mathematically grounded in primary sources. Generates interactive trace indicators (e.g. [Evidence #42]) within compiled documents, allowing absolute audibility.",
            "assets/tech_reports.png", "technology/grounded-decisions.html"
        ),
    ])
    
    return f"""
<section class="home-hero-v2" aria-labelledby="home-hero-heading">
  <div class="hero-v2-copy">
    <p class="eyebrow">Local-first AI UX research workspace</p>
    <h1 id="home-hero-heading">Open-source UX Research agents and tools. Human-in-the-loop AI for UXR.</h1>
    <p class="hero-lede">Istara is a local-first agentic platform for UX Research. Donate AI compute between computers to one single Istara server and have many agents working together on different UX tasks, using 50+ UX skills and agents that self-evolve. Keep data local and encrypted, secure access for teams.</p>
    <div class="hero-v2-actions">
      <a class="primary-action" href="#install">Install Istara</a>
      <a class="secondary-action" href="docs.html">Explore Docs Hub</a>
      <a href="https://github.com/henrique-simoes/Istara" class="github-action">GitHub</a>
    </div>
    <div class="hero-command-card" aria-label="Recommended install command">
      <div>
        <span>Recommended on macOS</span>
        <code>{html.escape(PRIMARY_INSTALL)}</code>
      </div>
      {_copy_button(PRIMARY_INSTALL, "Copy")}
    </div>
  </div>
  <div class="hero-v2-product" aria-label="Istara research swarm visualization">
    <img src="assets/istara_presentation.gif" alt="Istara presentation" class="hero-presentation-gif">
    <div class="spine-visual">
      <div class="node active">
        <span class="dot"></span>
        <span class="label">Raw Ingestion</span>
      </div>
      <div class="connector"></div>
      <div class="node active">
        <span class="dot"></span>
        <span class="label">Multi-Model Extraction</span>
      </div>
      <div class="connector"></div>
      <div class="node active">
        <span class="dot"></span>
        <span class="label">Human Reconciliation</span>
      </div>
      <div class="connector"></div>
      <div class="node active">
        <span class="dot"></span>
        <span class="label">Traceable Decisions</span>
      </div>
    </div>
  </div>
</section>
<ul class="hero-proof-list" aria-label="Istara homepage proof points">{proofs_html}</ul>

<section id="install" class="install-section-v2" aria-labelledby="install-heading">
  <div class="section-heading">
    <div>
      <p class="eyebrow">Install first</p>
      <h2 id="install-heading">Start with the shortest path, then keep the docs nearby.</h2>
    </div>
    <p>The homepage keeps installation visible because the fastest path to understanding Istara is running it with your own research project.</p>
  </div>
  <div class="install-grid">
    {_install_card("Recommended on macOS", "Homebrew cask", "Use the managed cask for the simplest install and update flow.", PRIMARY_INSTALL, primary=True)}
    {_install_card("macOS / Linux", "Shell installer", "Use the repository installer when you want a guided command-line setup.", SHELL_INSTALL)}
    {_install_card("Development / Windows notes", "Source checkout", "Use the repository for development, Docker-based work, and current platform notes.", SOURCE_INSTALL)}
  </div>
</section>

<section id="product-tour" class="section-block capabilities-bento" aria-labelledby="capabilities-heading">
  <div class="section-heading">
    <div>
      <p class="eyebrow">Core Swarm Capabilities</p>
      <h2 id="capabilities-heading">Equip your team with five specialized AI agents.</h2>
    </div>
    <p>Run focused UX research skills and maintain complete control over how data is processed, analyzed, and stored.</p>
  </div>
  <div class="tech-sections-container">
    {swarm_sections_html}
  </div>
</section>

<section id="main-features" class="section-block bento-details" aria-labelledby="features-heading">
  <div class="section-heading">
    <div>
      <p class="eyebrow">Technical Architecture</p>
      <h2 id="features-heading">Built around one research process, not scattered AI tools.</h2>
    </div>
    <p>Every feature that touches research data should either enter the Research Spine or consume accepted evidence from it.</p>
  </div>
  <div class="tech-sections-container">
    {arch_sections_html}
  </div>
</section>

<section class="section-block skills-showcase-section" aria-labelledby="skills-showcase-heading">
  <div class="section-heading">
    <div>
      <p class="eyebrow">Equip Your Swarm</p>
      <h2 id="skills-showcase-heading">53 Governed UX Research Skills by Double Diamond Category</h2>
    </div>
    <p>Every skill executes securely inside the Research Spine and records execution health, model-routing stats, and prompt evolution proposals.</p>
  </div>
  <div class="skills-categories-grid">
    <div class="skill-cat-card">
      <h4>🔍 Discover Phase</h4>
      <span class="skills-count">14 Skills</span>
      <ul>
        <li>User Interviews</li>
        <li>Contextual Inquiry</li>
        <li>Survey Design & Ingest</li>
        <li>Competitive Analysis</li>
        <li>Diary Studies</li>
        <li>Survey AI Response Detection</li>
      </ul>
    </div>
    <div class="skill-cat-card">
      <h4>🎯 Define Phase</h4>
      <span class="skills-count">12 Skills</span>
      <ul>
        <li>Thematic Analysis (Inductive)</li>
        <li>Kappa Inter-Coder Analysis</li>
        <li>Affinity Mapping</li>
        <li>Empathy Mapping</li>
        <li>JTBD & Persona Creation</li>
        <li>Journey & Flow Mapping</li>
      </ul>
    </div>
    <div class="skill-cat-card">
      <h4>🛠️ Develop Phase</h4>
      <span class="skills-count">10 Skills</span>
      <ul>
        <li>Usability Testing Analysis</li>
        <li>Heuristic Evaluation</li>
        <li>Cognitive Walkthrough</li>
        <li>Card Sorting & Tree Testing</li>
        <li>A/B Test Analysis</li>
        <li>Design Critique</li>
      </ul>
    </div>
    <div class="skill-cat-card">
      <h4>📦 Deliver Phase</h4>
      <span class="skills-count">10 Skills</span>
      <ul>
        <li>Design System Audit</li>
        <li>SUS/UMUX Usability Scoring</li>
        <li>NPS Driver Analysis</li>
        <li>Developer Handoff Docs</li>
        <li>Regression Impact Analysis</li>
        <li>Longitudinal Tracking</li>
      </ul>
    </div>
    <div class="skill-cat-card full-row">
      <h4>⚙️ Cross-Phase Metacognitive Skills (7 Skills)</h4>
      <div class="skills-list-inline">
        <span>Agent Factory</span>
        <span>Skill Evolution</span>
        <span>UX Law Auditing</span>
        <span>Evidence Chain Validator</span>
        <span>Multi-model Validator</span>
        <span>Autoresearch Optimizer</span>
      </div>
    </div>
  </div>
</section>

<section id="research-flow" class="section-block research-flow-section" aria-labelledby="research-flow-heading">
  <div class="research-flow-copy">
    <p class="eyebrow">How evidence becomes reportable</p>
    <h2 id="research-flow-heading">From source material to approved reports.</h2>
    <p>Atomic research findings become trusted only after source-grounded extraction, coding, reliability checks, reconciliation, and human-approved Done tasks.</p>
  </div>
  <ol class="research-flow-rail">
    <li><span>01</span><strong>Sources Ingestion</strong></li>
    <li><span>02</span><strong>Evidence Units</strong></li>
    <li><span>03</span><strong>Independent Coding</strong></li>
    <li><span>04</span><strong>Ensemble Reliability</strong></li>
    <li><span>05</span><strong>Human Reconciliation</strong></li>
    <li><span>06</span><strong>Accepted Atoms & Insights</strong></li>
    <li><span>07</span><strong>Approved Done Tasks</strong></li>
    <li><span>08</span><strong>Traceable Reports</strong></li>
  </ol>
</section>
"""
