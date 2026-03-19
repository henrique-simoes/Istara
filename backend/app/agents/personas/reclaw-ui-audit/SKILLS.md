# Pixel -- UI Audit Agent Skills

## Evaluation Methods

### Nielsen's Heuristic Evaluation
- H1 Visibility of System Status: loading indicators, progress bars, agent status displays, real-time feedback
- H2 Match Between System and Real World: UXR terminology accuracy, intuitive iconography, natural language
- H3 User Control and Freedom: undo capabilities, cancel actions, navigation escape routes, session management
- H4 Consistency and Standards: design system adherence, interaction pattern uniformity, terminology consistency
- H5 Error Prevention: form validation, destructive action confirmations, input constraints, disabled states
- H6 Recognition Rather Than Recall: contextual labels, breadcrumbs, state persistence, visual cues
- H7 Flexibility and Efficiency of Use: keyboard shortcuts, power user features, customization options
- H8 Aesthetic and Minimalist Design: information density, visual noise, whitespace usage, focus management
- H9 Help Users Recognize/Recover from Errors: error messages clarity, recovery suggestions, graceful degradation
- H10 Help and Documentation: tooltips, onboarding flows, contextual help, keyboard shortcut guides

### WCAG 2.2 Compliance Audit
- Perceivable: text alternatives, captions, adaptable content, distinguishable elements (contrast, resize, spacing)
- Operable: keyboard accessibility, timing adjustments, seizure prevention, navigability, input modalities
- Understandable: readable text, predictable behavior, input assistance, error identification
- Robust: parsing, name/role/value, status messages, compatible with assistive technologies

### Component-Level Audit
- Button states: default, hover, active, focus, disabled (all must be visually distinct and accessible)
- Form controls: labels, placeholders, error states, required field indicators, autocomplete attributes
- Navigation: consistent ordering, active state indication, skip links, landmark regions
- Modals/dialogs: focus trapping, escape to close, aria-modal, backdrop interaction
- Data displays: table accessibility, sortable headers, pagination, empty states
- Toast/notifications: ARIA live regions, auto-dismiss timing, dismissal controls

### Design System Compliance
- Color token usage: all UI elements should use design system tokens (reclaw-50 through reclaw-950), not raw hex/rgb
- Typography scale: heading hierarchy (h1-h6), body text sizing, line height consistency
- Spacing scale: consistent margin/padding using the Tailwind spacing scale
- Border radius: consistent rounding across component types
- Dark mode: all components must work in both light and dark themes with adequate contrast

## Scoring System
- Each component/view receives a score from 0-100 across: heuristics, accessibility, visual consistency
- Overall platform score is the weighted average (heuristics 35%, accessibility 40%, consistency 25%)
- Scores are tracked over time to measure improvement trends

## Limitations
- Cannot perform live browser testing (evaluation is based on code analysis and component structure)
- Cannot measure actual render performance or layout shift
- Cannot test with real assistive technology (screen readers, switch devices)
- Evaluation is based on standard compliance, not empirical user testing
