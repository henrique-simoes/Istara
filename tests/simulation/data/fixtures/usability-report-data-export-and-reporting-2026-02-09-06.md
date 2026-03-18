# Usability Test Report — Data Export and Reporting

**Date:** 2026-02-09
**Product:** Expense management and invoicing tool (FinLedger)
**Research Goal:** Reduce average report generation time and eliminate top 3 export errors
**Participants:** 7 (Frontend Developer, Account Executive, UX Designer, Engineering Director, Project Manager, Support Specialist, Product Manager)
**Methodology:** Moderated remote usability testing with think-aloud protocol

## Participants

| ID | Name | Role | Company Size | Age |
|----|------|------|-------------|-----|
| P12 | Sofia Rossi | Frontend Developer | 50-200 | 27 |
| P23 | Michael Torres | Account Executive | 500-2000 | 46 |
| P03 | Priya Patel | UX Designer | 10-50 | 28 |
| P02 | Marcus Johnson | Engineering Director | 500-2000 | 45 |
| P13 | Tomás García | Project Manager | 200-500 | 39 |
| P17 | Liam Murphy | Support Specialist | 50-200 | 25 |
| P01 | Sarah Chen | Product Manager | 50-200 | 32 |

## Tasks

### Task 1: Export raw data as CSV

- **Completion rate:** 70%
- **Average time:** 142s
- **Errors observed:** 0
- **Participant observations:**
  - Sofia Rossi (Frontend Developer): "The date picker doesn't let me type a date manually, I have to click through months one by one"
  - Marcus Johnson (Engineering Director): "Every time I export a report, the formatting is completely off and I have to fix it in Excel"
  - Sarah Chen (Product Manager): "I accidentally deleted a project and there was no way to undo it"

### Task 2: Create a chart from exported data within the app

- **Completion rate:** 58%
- **Average time:** 158s
- **Errors observed:** 3
- **Participant observations:**
  - Liam Murphy (Support Specialist): "Switching between projects is painfully slow, there's no quick switcher"
  - Michael Torres (Account Executive): "I think the biggest issue is just consistency, some parts feel modern and others feel like they haven't been updated in years"
  - Sofia Rossi (Frontend Developer): "When I share a link with my team, they always have to log in again even if they already have accounts"

### Task 3: Customize the columns included in an export

- **Completion rate:** 89%
- **Average time:** 103s
- **Errors observed:** 1
- **Participant observations:**
  - Marcus Johnson (Engineering Director): "The file upload limit is way too small for the kind of documents we work with"
  - Sarah Chen (Product Manager): "It sends me way too many email notifications and I can't figure out how to turn them off individually"
  - Michael Torres (Account Executive): "The drag-and-drop interface is really satisfying when it works, but sometimes items just snap to the wrong place"
  - Sofia Rossi (Frontend Developer): "It took me two weeks to realize there was a bulk edit feature hidden in a dropdown"

### Task 4: Generate a monthly summary report

- **Completion rate:** 63%
- **Average time:** 80s
- **Errors observed:** 2
- **Participant observations:**
  - Sofia Rossi (Frontend Developer): "I had to watch a YouTube tutorial to understand the reporting feature, and that shouldn't be necessary"
  - Priya Patel (UX Designer): "The loading time is really frustrating, especially when I'm trying to pull up something in a meeting"
  - Michael Torres (Account Executive): "I keep getting logged out randomly in the middle of my work"

### Task 5: Filter report data before exporting

- **Completion rate:** 72%
- **Average time:** 19s
- **Errors observed:** 1
- **Participant observations:**
  - Priya Patel (UX Designer): "The mobile app is fine for checking things, but I'd never try to do real work on it"
  - Sofia Rossi (Frontend Developer): "My manager asked me to pull a report and it took me forty-five minutes to figure out how"
  - Tomás García (Project Manager): "The mobile app is fine for checking things, but I'd never try to do real work on it"
  - Marcus Johnson (Engineering Director): "I use it every single day, so even small annoyances add up over time"

### Task 6: Share a report link with a stakeholder

- **Completion rate:** 97%
- **Average time:** 39s
- **Errors observed:** 0
- **Participant observations:**
  - Marcus Johnson (Engineering Director): "The color contrast is so low I can barely read the secondary text"
  - Liam Murphy (Support Specialist): "Every time I export a report, the formatting is completely off and I have to fix it in Excel"

## SUS Score

**Overall SUS Score: 56 / 100** — Grade: C — OK (below average for usability)

The system scores below the industry average (68), indicating significant usability concerns that should be addressed before the next release.

## Key Findings

1. **[Critical]** 3 out of 5 participants attempted to use the back button instead of the in-app navigation, causing loss of form state.
2. **[Major]** Form validation only triggered on submit, not inline, causing repeated correction cycles.
3. **[Major]** Users consistently hesitated before clicking the primary CTA — the label was ambiguous.
4. **[Major]** The loading state provided no progress indication, leading two participants to refresh the page.
5. **[Minor]** The tooltip text was truncated on smaller screens, hiding critical information.
6. **[Minor]** The modal dialog could not be dismissed with the Escape key, violating accessibility expectations.

## Recommendations

1. Increase color contrast ratios to meet WCAG AA standards across all interactive elements.
2. Improve empty states with actionable guidance to reduce user confusion on first use.
3. Add inline validation to multi-step forms to reduce error-correction cycles.
4. Add visible text labels alongside icon-only buttons in the toolbar.

---
*Report generated from usability testing session on 2026-02-09.*
*7 participants, 6 tasks evaluated.*