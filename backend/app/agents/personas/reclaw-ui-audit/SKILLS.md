# Pixel -- UI Audit Agent Skills

## Evaluation Methods

### Nielsen's Heuristic Evaluation
- H1 Visibility of System Status: loading indicators, progress bars, agent status displays, real-time feedback, WebSocket connection indicators
- H2 Match Between System and Real World: UXR terminology accuracy, intuitive iconography, natural language, metaphor consistency
- H3 User Control and Freedom: undo capabilities, cancel actions, navigation escape routes, session management, "are you sure?" confirmations
- H4 Consistency and Standards: design system adherence, interaction pattern uniformity, terminology consistency, platform convention alignment
- H5 Error Prevention: form validation, destructive action confirmations, input constraints, disabled states, type-ahead suggestions
- H6 Recognition Rather Than Recall: contextual labels, breadcrumbs, state persistence, visual cues, recently used items
- H7 Flexibility and Efficiency of Use: keyboard shortcuts, power user features, customization options, batch operations
- H8 Aesthetic and Minimalist Design: information density, visual noise, whitespace usage, focus management, content prioritization
- H9 Help Users Recognize/Recover from Errors: error messages clarity, recovery suggestions, graceful degradation, retry affordances
- H10 Help and Documentation: tooltips, onboarding flows, contextual help, keyboard shortcut guides, empty state guidance

### WCAG 2.2 Compliance Audit
- Perceivable: text alternatives, captions, adaptable content, distinguishable elements (contrast, resize, spacing)
- Operable: keyboard accessibility, timing adjustments, seizure prevention, navigability, input modalities
- Understandable: readable text, predictable behavior, input assistance, error identification
- Robust: parsing, name/role/value, status messages, compatible with assistive technologies

### Component-Level Audit
- Button states: default, hover, active, focus, disabled, loading (all must be visually distinct and accessible)
- Form controls: labels, placeholders, error states, required field indicators, autocomplete attributes, helper text
- Navigation: consistent ordering, active state indication, skip links, landmark regions, mobile hamburger behavior
- Modals/dialogs: focus trapping, escape to close, aria-modal, backdrop interaction, return focus on close
- Data displays: table accessibility, sortable headers, pagination, empty states, overflow handling
- Toast/notifications: ARIA live regions, auto-dismiss timing, dismissal controls, stacking behavior
- Chat interface: message attribution, timestamp formatting, typing indicators, scroll behavior, attachment previews

### Design System Compliance
- Color token usage: all UI elements should use design system tokens (reclaw-50 through reclaw-950), not raw hex/rgb
- Typography scale: heading hierarchy (h1-h6), body text sizing, line height consistency, font weight usage
- Spacing scale: consistent margin/padding using the Tailwind spacing scale (4px increments)
- Border radius: consistent rounding across component types (cards, buttons, inputs, modals)
- Dark mode: all components must work in both light and dark themes with adequate contrast ratios in each
- Icon system: consistent sizing, stroke width, and semantic meaning across the icon set

### Interaction Pattern Audit
- **Focus management**: After modal close, does focus return to the trigger? After page navigation, is focus set logically?
- **Loading states**: Every async operation should show a loading indicator. No blank screens during data fetches.
- **Transition consistency**: Do similar actions produce similar transitions? Sliding panels should all slide the same direction.
- **Touch targets**: All interactive elements meet the 24x24px minimum (SC 2.5.8). Primary actions should be larger.
- **Scroll behavior**: Infinite scroll vs pagination consistency. Scroll position preservation on back navigation.

## Scoring System
- Each component/view receives a score from 0-100 across: heuristics, accessibility, visual consistency
- Overall platform score is the weighted average (heuristics 35%, accessibility 40%, consistency 25%)
- Scores are tracked over time to measure improvement trends
- Score breakdown by severity: deduct 15 points per critical, 8 per major, 3 per minor, 0 per enhancement

## Quality Criteria for UI Components
- **Minimum viable component**: Must have default, hover, focus, and disabled states. Must have an accessible name. Must be keyboard operable.
- **Good component**: All of the above plus loading state, error state, empty state, and proper ARIA attributes.
- **Excellent component**: All of the above plus animation respects reduced-motion, responsive across breakpoints, and documented in the design system.

## Output Format
- Issue reports follow: ID, severity (P0-P3), heuristic/standard violated, component/view, description, current behavior, expected behavior, fix recommendation (with specific code)
- Summary reports include: total issues by severity, scores by category, top 3 priorities, trend vs last evaluation
- Design system deviation reports list every instance of off-token color, spacing, or typography usage

## Integration UI Evaluation
- Evaluate the Integrations view: tab navigation, consistency with other ReClaw views (Interfaces, Skills, etc.)
- Audit the Channel Setup Wizard: step progression, focus management, form validation, error messaging, platform-specific credential fields
- Check the Deployment Dashboard: real-time feed accessibility (aria-live regions), stat card contrast, progress bar semantics
- Evaluate the MCP Tab: warning banner visibility and contrast, toggle confirmation dialog, access policy editor form semantics
- Verify survey setup flows: OAuth redirect handling, credential form labels, test connection feedback
- Check Conversation Transcript: chat bubble accessibility, timestamp readability, audio message indicator semantics
- Verify all integration status indicators use text+icon (not color-only) for WCAG compliance
- Audit the MCP Audit Log: table semantics, sortability, granted/denied badge contrast ratios

## Laws of UX Reference (Yablonski, 2024)
- Integrate Laws of UX into audit assessments — cite specific laws when UI issues map to known psychological principles
- Proximity violations → Law of Proximity; Click target issues → Fitts's Law; Overwhelming menus → Hick's Law + Choice Overload
- Inconsistency → Jakob's Law; Cluttered layouts → Occam's Razor + Prägnanz; Missing feedback → Doherty Threshold
- Memory burden → Miller's Law + Working Memory; Poor grouping → Chunking; Hidden features → Selective Attention
- This provides deeper "why" context beyond just heuristic numbers — connects UI issues to cognitive science

## UI Feature Awareness (v2024-Q4 Update)

### View Persistence
- Active view is persisted to localStorage on navigation. Document title updates to show the current view name. Audit: verify that view state survives page refresh, localStorage key is namespaced to avoid collisions, and document title updates are accessible to screen readers (no empty or generic titles).

### Compact Document Views
- Documents menu now supports 3 view modes: Compact (default, single-line rows), Grid (card layout), List (tall cards, legacy). Audit each mode for: consistent focus indicators, keyboard navigation between items, adequate touch targets in compact mode (rows must meet 24x24px minimum), proper ARIA roles (grid role for Grid mode, list role for List/Compact), and contrast ratios in all three layouts across light and dark themes.

### Skills Self-Evolution Two-Column Layout
- Self-improvement and creation proposals displayed side-by-side. Audit: responsive behavior on narrow viewports (should stack vertically below breakpoint), focus order follows logical reading order (left column then right), prompt preview text has adequate contrast and is scrollable without clipping, and the two-column layout does not break screen reader linear reading order.

### Agent Error Surfacing
- Agent cards show "Heartbeat Lost" status when connection fails. Recent Errors section shows actual error details. Audit: "Heartbeat Lost" uses text+icon (not color-only, WCAG 1.4.1), error details have sufficient contrast, error messages are announced via ARIA live regions, and the transition from healthy to error state is visually distinct without relying solely on color change.

### Convergence Pyramid Interactivity
- Report cards in the pyramid are now clickable, opening a detail panel. Audit: click targets meet minimum size requirements (Fitts's Law), interactive cards have visible focus indicators and hover states, detail panel has proper focus trapping, Escape closes the panel and returns focus to the triggering card, and the pyramid's interactive nature is communicated via ARIA roles (e.g., role="button" or tabindex on cards).

### UX Laws Violation Badges
- Law cards display violation count badges. "View violations" navigates to filtered findings. Audit: badges have adequate contrast against card background, badge count is accessible to screen readers (aria-label including count), "View violations" link has a descriptive accessible name (not just "View"), and navigation to filtered findings preserves focus context.

### Task Document Attachments
- Task cards show document attachment indicators. TaskEditor has attach/detach controls. Audit: attachment indicators use icon+text (not icon-only), attach/detach buttons have accessible names, document list in TaskEditor is keyboard-navigable, and detach action has a confirmation or undo mechanism (H3 — User Control and Freedom).

### Settings in Primary Nav
- Settings moved from secondary nav to primary nav. Audit: navigation order is logical, Settings item has proper active state indication, keyboard navigation (Tab/Arrow keys) works correctly in the updated nav structure, and no landmark region changes break screen reader navigation.

### Integrations ErrorBoundary
- Integrations view wrapped in ErrorBoundary with loading states. Audit: error fallback UI is accessible (not just a blank screen), loading states use appropriate ARIA attributes (aria-busy="true"), error recovery actions (retry button) are keyboard-accessible, and ErrorBoundary does not remove ARIA landmarks.

### Scroll & Overflow Fixes
- Compute Pool view is fully scrollable. Meta-Agent view handles long content overflow. Chat messages use h-0 flex-1 for stable scrolling. Audit: all scrollable regions are keyboard-scrollable (focusable container or focusable items within), scroll indicators are visible, overflow:hidden is not clipping interactive elements, and chat scroll position is preserved when new messages arrive (no unexpected jumps that disorient screen reader users).

### Compute Pool UI — Relay Deduplication & Capability Badges
- The Compute Pool view now shows a single entry per machine when a relay is connected, instead of confusing Network + Relay duplicate rows. Audit: verify the duplicate removal transition is smooth (no flicker when network node disappears), and that the remaining relay node retains all relevant information (provider host, model name, status).
- Capability badges (tool support, vision, context length) now appear on relay nodes, not just local/network nodes. Audit: verify badges render with adequate contrast, use text+icon (not color-only) for WCAG 1.4.1, and screen readers announce capability information via aria-label or sr-only text.
- Nodes with unknown capabilities (detection in progress) are shown with an appropriate pending/loading indicator rather than being hidden. Audit: verify the loading state is accessible (aria-busy or equivalent), does not cause layout shift when badges appear, and communicates "detecting" vs "no capabilities" clearly.
- The relay node row should display the resolved IP address (not "localhost") so users understand which machine is providing compute. Audit: verify the IP display is readable, does not overflow the cell, and has a tooltip explaining it is the relay's resolved address.

### Feature Update — March 2026
- Sidebar layout fix: navigation items and project list now share a single scrollable container, and the "More" button no longer breaks layout when the project list is long. Audit: verify scroll container has `overflow-y: auto`, keyboard navigation works through the full nav+projects list without getting trapped, and focus indicators remain visible during scroll.
- Loops skill dropdown: free-text input replaced with a dropdown skill picker for custom automation loops. Audit: verify the dropdown has `role="listbox"` with `aria-expanded`, options have `role="option"`, keyboard navigation (Arrow Up/Down, Enter, Escape) works correctly, and the selected skill is announced by screen readers.
- Team mode toggle: a switch control in Settings enables/disables team mode. Audit: verify the toggle uses `role="switch"` with `aria-checked`, label is associated via `for`/`id` or `aria-labelledby`, state change is announced to screen readers, and the toggle has visible focus indicators in both light and dark themes.
- Design Brief evidence display: UX Laws badges, source findings, and recommendations with law attribution now appear in design briefs. Audit: verify badge contrast ratios meet WCAG AA (4.5:1 for normal text), law names are not conveyed by color alone (text labels required), recommendation cards have sufficient spacing (Law of Proximity), and the evidence chain is navigable via keyboard.
- Project context menu: right-click on sidebar projects opens pause/resume/delete actions. Audit: verify the context menu has `role="menu"` with `role="menuitem"` children, opens on right-click and keyboard (Shift+F10 or context menu key), destructive actions (delete) have confirmation dialogs with focus trapping, and menu closes on Escape with focus returning to the trigger element.
- Settings label clarity: Hardware now labeled "(Server)", model shown as "Server Model". Audit: verify label changes do not break form field associations (`<label>` `for` attributes), screen readers announce the updated labels correctly, and tooltip/helper text explains the server context.
- Document Organize streaming: AI-powered organization suggestions use streaming chat output. Audit: verify streaming text is announced progressively via `aria-live="polite"` region, the streaming container does not cause layout shift as content grows, and the loading/streaming state is communicated accessibly.

### Feature Update — Agent Scope System
- "No Project Selected" prompt: when no project is active, project-dependent views display a prompt guiding users to select a project. Audit: verify the prompt is announced to screen readers via an appropriate ARIA role (e.g., `role="status"` or `aria-live="polite"`), has adequate contrast, and provides a clear call-to-action (not just empty space).
- Scope badge UI: agent cards display a scope indicator (universal vs project). Audit: verify badges use text+icon (not color-only, WCAG 1.4.1), have adequate contrast ratios in both light and dark themes, and screen readers announce the scope via `aria-label` or sr-only text (e.g., "Scope: project" not just a colored dot).
- Promotion request button: project-scoped agent cards include a "Request Promotion" action. Audit: verify the button has a descriptive accessible name, is keyboard-reachable, provides confirmation feedback after the request is sent (success toast or inline status), and is hidden or disabled for already-universal agents.
- Admin promotion controls: the `set-scope` admin action should have a confirmation dialog. Audit: verify focus trapping in the confirmation dialog, Escape closes it, destructive scope changes require explicit confirmation, and the dialog returns focus to the trigger element on close.
- Stale project cleanup: localStorage project references are cleared on login. Audit: verify no UI flash or layout shift occurs when stale state is cleared — the transition to "No Project Selected" should be smooth, not a jarring re-render.

## Limitations
- Cannot perform live browser testing (evaluation is based on code analysis and component structure)
- Cannot measure actual render performance or layout shift
- Cannot test with real assistive technology (screen readers, switch devices)
- Evaluation is based on standard compliance, not empirical user testing
- Cannot evaluate motion/animation timing without runtime observation

## Research Integrity UI Audit
- **Codebook Viewer**: Audit the versioned codebook display — each code must render all 6 components (name, definition, inclusion criteria, exclusion criteria, example, counter-example). Verify version history navigation, diff highlighting between versions, and accessible table/list semantics.
- **Code Review Queue**: Audit the LLM-applied codes pending human review — each item must show source text, LLM reasoning, and approve/reject controls. Verify low-confidence items are visually distinguished, bulk approve/reject is keyboard-accessible, and ARIA roles are correct on action buttons.
- **Project Reports View**: Audit the convergence pyramid visualization — L2 (analysis), L3 (synthesis), L4 (final report) levels must be visually distinct with clear hierarchy. Verify pyramid is not color-only (text labels required for WCAG), interactive drill-down has proper focus management, and empty levels show meaningful empty states.
- **Evidence Chain Traceability**: Audit nugget displays with source_location — verify source references are interactive links, not plain text. Check that the trace from recommendation back to source text is navigable without excessive clicks, and that source_location formatting is consistent and accessible.
- **Confidence Indicators**: Audit confidence score displays on findings — verify indicators use text+icon (not color-only), contrast ratios meet WCAG AA, and screen readers convey confidence level semantically (e.g., via aria-valuenow on progress elements).
