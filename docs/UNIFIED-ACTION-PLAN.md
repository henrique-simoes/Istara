# ReClaw — Unified Action Plan

**Date:** 2026-03-14  
**Source:** Synthesized from DevOps, UI, and UX audits  
**North Star Metric:** Time from first launch to first validated insight with evidence chain — **target under 10 minutes**

---

## Already Fixed ✅ (excluded from this plan)

- psutil + pyyaml in requirements.txt (C1, C2)
- ContextDocument table imported in init_db (H1, M1)
- SQL injection in LanceDB delete (H3)
- `--reload` removed from Dockerfile (H4)
- Memory leak in page.tsx event listener (UI P0-1)
- Duplicate Cmd+K listeners (UI P0-2)
- Route ordering for `/skills/health/all` etc. (M4)
- Settings mutation thread-safety (H2)
- UserSimAgent API_BASE configurable (M2)

---

## MVP Definition of Done

Before first public release, **all P0 and P1 items must be complete**, plus:

- [ ] User can install with one command (`docker compose up`)
- [ ] First-run experience guides user from launch → project → upload → first insight
- [ ] Chat works with local Ollama model (Qwen 3.5)
- [ ] File upload → automatic nugget extraction works end-to-end
- [ ] Findings view shows nuggets with source citations
- [ ] Evidence chain drilldown (nugget → fact → insight) is functional, not stub
- [ ] Errors surface to users (not just console.error)
- [ ] No runtime crashes on happy path
- [ ] Interview/transcript upload + analysis works (via Chat at minimum)
- [ ] README has install, quick-start, and architecture docs

---

## Action Items

### P0 — Blocking (must fix before any release)

| # | Item | Package | Effort | Notes |
|---|------|---------|--------|-------|
| 1 | **Wrap `renderView()` in ErrorBoundary** | Frontend | S | One component crash kills the entire app. Add fallback with "Go back to Chat" escape hatch. |
| 2 | **Surface errors to users (replace console.error)** | Frontend | M | Nearly every component swallows errors. Create a `useApiCall` hook or `<DataLoader>` wrapper that shows error state + retry. Affects: ChatView, FindingsView, SettingsView, RightPanel, InterviewView, MetricsView. |
| 3 | **Add root ErrorBoundary in layout.tsx** | Frontend | S | Unhandled errors crash the whole app with a white screen. |
| 4 | **Ollama connection check on startup** | Frontend | S | If Ollama isn't running, show a blocking modal with setup instructions instead of a confusing chat error. |
| 5 | **Fix chat session leak on client disconnect** | Backend | M | SSE generator uses outer-scope DB session. Use separate `async_session()` inside generator or handle `GeneratorExit`. (M3 from DevOps) |
| 6 | **Create `data/watch` directory in install script** | Infra | S | Docker creates it as root-owned otherwise. Add `mkdir -p` to install.sh. (M5 from DevOps) |

### P1 — Critical UX (next sprint)

| # | Item | Package | Effort | Notes |
|---|------|---------|--------|-------|
| 7 | **Build first-run onboarding (3-step modal)** | Frontend | M | Welcome → Create project (with optional sample/template) → Upload first file. Progressive nav reveal: show Chat first, unlock others as data appears. This is the single biggest UX gap. |
| 8 | **Make Interview View functional** | Frontend | L | Currently a placeholder. Must: render actual transcript content (not placeholder text), support batch upload, trigger analysis directly (not redirect to Chat). Audio playback and inline highlighting can wait (P2). This is the #1 workflow for target users. |
| 9 | **Make search results clickable** | Frontend | S | Click a result → navigate to that finding in Findings View. Currently a dead end. |
| 10 | **Add focus traps to all modals** | Frontend | S | SearchModal, AtomicDrilldown — Tab escapes to background. Create a reusable `<FocusTrap>` component. |
| 11 | **Add confirmation dialogs for destructive actions** | Frontend | S | Delete task (KanbanBoard), rollback (VersionHistory). No confirmation currently. |
| 12 | **Implement actual evidence chain in AtomicDrilldown** | Frontend | M | `buildChain()` is a stub (just slices arrays). Must follow real relationships: recommendation → insights → facts → nuggets → sources. |
| 13 | **Add loading states consistently** | Frontend | S | Use existing LoadingSkeleton component (currently underused). Add to: ChatView, FindingsView, MetricsView, RightPanel. |
| 14 | **Wire up stub buttons** | Frontend | M | InterviewView quick actions, VersionHistory rollback — buttons exist with no onClick handlers. Either implement or remove them. |

### P2 — Important (next 2 sprints)

| # | Item | Package | Effort | Notes |
|---|------|---------|--------|-------|
| 15 | **Simplify navigation from 8 → 5 items** | Frontend | M | Chat, Findings (absorb Interviews + Metrics as tabs), Tasks, Context, Dashboard (new). Move Settings to header ⚙️, History to project dropdown. Reduces cognitive load ~37%. |
| 16 | **Add ARIA labels and semantic roles** | Frontend | M | All icon-only buttons need `aria-label`. Modals need `role="dialog" aria-modal="true"`. Tabs need `role="tablist/tab/tabpanel"`. Nav needs `role="navigation"`. Toast needs `aria-live`. Current accessibility: D grade. |
| 17 | **Add keyboard navigation** | Frontend | M | Arrow keys for tabs (FindingsView), search results (SearchModal), Kanban columns. Keyboard-accessible DnD alternative for Kanban (dropdown to move columns). |
| 18 | **Implement URL-based routing** | Frontend | L | No browser back/forward, no deep linking, no shareable URLs. Use Next.js App Router or query params. |
| 19 | **Add cancel button for streaming responses** | Frontend | S | ChatView has no way to abort a streaming response. |
| 20 | **Context feedback loop** | Frontend | M | "What I know" preview button showing composed context the agent sees. Guardrail enforcement visibility in chat. Users can't verify context is being used. |
| 21 | **Task card editing and skill assignment** | Frontend | M | Kanban cards are create-only. Add: inline title/description editing, skill selector dropdown, editable user_context, priority field. |
| 22 | **SettingsView: add model switching** | Frontend | M | Currently read-only. Backend has `switch_model` endpoint but UI has no way to trigger it. Add model selector cards. |
| 23 | **Add semantic search via vector DB** | Backend | M | Search is client-side `includes()` over all findings. Won't scale. Backend already has LanceDB — expose a search endpoint. |
| 24 | **Add skip-to-content link** | Frontend | S | WCAG 2.4.1. `<a href="#main-content" className="sr-only focus:not-sr-only">`. |
| 25 | **Clean up dead code** | Backend | S | `skill_loader.py` is orphaned (never imported). Unused SQLAlchemy imports in `context_hierarchy.py`. Move `import json` to top of `ollama.py`. (L3, L4, L5 from DevOps) |

### P3 — Polish (backlog)

| # | Item | Package | Effort | Notes |
|---|------|---------|--------|-------|
| 26 | **Add celebration/progress moments** | Frontend | S | First finding confetti/animation, phase completion markers, weekly research summary. Emotional payoff is missing. |
| 27 | **Build glossary and tooltip system** | Frontend | M | Hover tooltips for "Nugget," "Fact," "Insight," etc. `?` icons in section headers. First-time annotations. |
| 28 | **Responsive/mobile layout** | Frontend | L | No mobile layout at all. Spec calls for bottom nav on narrow screens. Right panel overlaps on small screens. |
| 29 | **Drag-and-drop file upload in ChatView** | Frontend | S | Spec mentions it, not implemented. |
| 30 | **Audio playback with transcript sync** | Frontend | XL | InterviewView spec shows audio player synced to transcript. Major feature. |
| 31 | **Inline nugget highlighting in transcripts** | Frontend | L | Click-to-highlight for manual nugget tagging in InterviewView. |
| 32 | **Connect MetricsView to actual data** | Frontend | M | All values are hardcoded placeholders. Needs API integration. |
| 33 | **Right panel redesign** | Frontend | M | Currently duplicates Findings. Should: show semantically-relevant findings in Chat, inline evidence chain in Findings, task-linked findings in Tasks. |
| 34 | **Add keyboard shortcut cheat sheet** | Frontend | S | `⌘1-5` for views, `⌘N` for new task, `⌘.` for right panel toggle, `?` to show cheat sheet. |
| 35 | **Dark mode flash prevention** | Frontend | S | Add blocking `<script>` in `<head>` to read theme before render. |
| 36 | **Diff view in VersionHistory** | Frontend | L | Spec mentions [View Diff] — not implemented. |
| 37 | **Auto-save with unsaved changes warning** | Frontend | S | ContextEditor has no unsaved changes detection. User can navigate away and lose edits. |
| 38 | **Toast action buttons for suggestions** | Frontend | S | Spec shows [Yes] [Not now] [Never] on suggestion toasts. Currently no action buttons. |
| 39 | **Cross-project search and dashboard** | Frontend | L | No way to search across projects or compare findings. Vision doc mentions team-wide knowledge base. |
| 40 | **Version from package.json** | Frontend | S | StatusBar hardcodes `v0.1.0`. |
| 41 | **Add `models/__init__.py` re-exports** | Backend | S | Minor DX convenience. (L1 from DevOps) |
| 42 | **Documentation: README, architecture, contributing** | Docs | M | Install guide, quick-start, architecture overview, contributing guide. |

---

## Work Package Summary

| Package | P0 | P1 | P2 | P3 | Total |
|---------|----|----|----|----|-------|
| **Frontend** | 4 | 7 | 8 | 14 | 33 |
| **Backend** | 1 | 0 | 2 | 1 | 4 |
| **Infrastructure** | 1 | 0 | 0 | 0 | 1 |
| **Documentation** | 0 | 0 | 0 | 1 | 1 |
| **Skills** | 0 | 0 | 0 | 0 | 0 |

**Frontend dominates.** The backend is solid; the frontend needs the most work.

---

## Sprint Recommendations

### Sprint 1 (Week 1): Stability + Onboarding
Items: 1, 2, 3, 4, 6, 7, 13  
**Goal:** App doesn't crash, errors are visible, new users get guided.

### Sprint 2 (Week 2): Core Workflows
Items: 5, 8, 9, 10, 11, 12, 14  
**Goal:** Interview view works, search is actionable, evidence chain is real, destructive actions are safe.

### Sprint 3 (Week 3): UX Quality
Items: 15, 16, 17, 19, 20, 21, 22, 24, 25  
**Goal:** Navigation simplified, accessibility passable, task management functional.

### Sprint 4 (Week 4): Scale + Polish
Items: 18, 23, 26, 27, 37, 42  
**Goal:** URL routing, semantic search, emotional design, docs for public release.

---

## Resolved Contradictions

| Topic | DevOps View | UI View | UX View | Resolution |
|-------|-------------|---------|---------|------------|
| Interview View priority | Not flagged | Score 6/10, needs audio/DnD | #1 priority, make-or-break | **Agree with UX**: Interview View is the critical path. Build functional transcript rendering first (P1), audio/highlighting later (P3). |
| Navigation count | Not flagged | Lists all 8 views | Reduce to 5 | **Agree with UX**: Simplify to 5. But do it in Sprint 3 (P2) after core workflows work. |
| Settings mutability | Thread-safety risk (H2) | Needs model switching UI | Not flagged | **Already fixed** thread-safety. UI model switching is P2. |
| Right panel value | Not flagged | Score 7/10, adequate | Redesign needed, duplicates content | **Agree with UX** for P3. Current version is fine for MVP. |

---

*This plan drives the next development sprint. Review weekly, adjust priorities based on user feedback.*
