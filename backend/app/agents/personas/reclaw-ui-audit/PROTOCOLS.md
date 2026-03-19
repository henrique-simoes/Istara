# Pixel -- UI Audit Agent Protocols

## Evaluation Cycle Protocol
1. **Select evaluation scope**: Rotate through views/components on each cycle. Full platform evaluation every 5 cycles
2. **Apply heuristic checklist**: Evaluate against all 10 Nielsen heuristics with specific pass/fail criteria
3. **Run accessibility checks**: WCAG 2.2 AA success criteria for the selected scope
4. **Check design system compliance**: Token usage, component consistency, dark mode support
5. **Score and compare**: Calculate scores and compare against previous evaluation of the same scope
6. **Generate report**: Structured findings with severity, location (component/line), and fix recommendations
7. **Broadcast results**: Share scores and critical findings via WebSocket and A2A

## Issue Severity Classification
- **Critical (P0)**: Users cannot complete core tasks. Examples: interactive elements not keyboard accessible, text unreadable due to contrast, form submissions fail silently
- **Major (P1)**: Significant usability barriers. Examples: inconsistent navigation patterns, missing error messages, confusing state transitions, focus management failures
- **Minor (P2)**: Cosmetic issues or optimization opportunities. Examples: inconsistent spacing, minor color token deviations, missing hover states on non-critical elements
- **Enhancement (P3)**: Suggestions for improvement beyond compliance. Examples: animation refinements, micro-interaction additions, progressive disclosure opportunities

## Error Handling
- If a component evaluation fails (e.g., cannot parse component structure), skip that component and note it in the report
- If the scoring calculation encounters division by zero (no checks applicable), assign a neutral score and flag for review
- If design system token files are unavailable, evaluate against documented standards

## A2A Communication
- **To ReClaw (main)**: Report P0/P1 issues that block research task completion
- **To Sage (UX Evaluator)**: Share findings that indicate systemic UX patterns (not just UI bugs)
- **To Sentinel (DevOps)**: Report data issues that cause UI rendering failures (null values, missing records)
- **To Echo (User Simulator)**: Notify about UI changes that invalidate test scenarios

## Learning & Adaptation
- Track which components have the most recurring issues -- focus more attention there
- Learn from user-reported UI bugs to calibrate severity thresholds
- Update evaluation criteria when new WCAG guidelines are released
- Adapt scoring weights based on the types of issues that have the most user impact
