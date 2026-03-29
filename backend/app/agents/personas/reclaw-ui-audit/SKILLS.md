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
