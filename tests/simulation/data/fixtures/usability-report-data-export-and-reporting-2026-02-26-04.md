# Usability Test Report — Data Export and Reporting

**Date:** 2026-02-26
**Product:** Fleet tracking and route optimization dashboard (ShipRoute Global)
**Research Goal:** Reduce average report generation time and eliminate top 3 export errors
**Participants:** 6 (VP of Product, CTO, UX Researcher, Product Owner, UX Designer, Engineering Director)
**Methodology:** Moderated remote usability testing with think-aloud protocol

## Participants

| ID | Name | Role | Company Size | Age |
|----|------|------|-------------|-----|
| P11 | David Okonkwo | VP of Product | 500-2000 | 48 |
| P15 | Derek Washington | CTO | 10-50 | 52 |
| P24 | Zainab Osei | UX Researcher | 50-200 | 24 |
| P30 | Omar Hassan | Product Owner | 200-500 | 35 |
| P03 | Priya Patel | UX Designer | 10-50 | 28 |
| P02 | Marcus Johnson | Engineering Director | 500-2000 | 45 |

## Tasks

### Task 1: Filter report data before exporting

- **Completion rate:** 40%
- **Average time:** 91s
- **Errors observed:** 4
- **Participant observations:**
  - Priya Patel (UX Designer): "I keep a sticky note on my monitor with the steps to do the export because it's not intuitive at all"
  - David Okonkwo (VP of Product): "It does what I need about eighty percent of the time, the other twenty percent I work around"
  - Derek Washington (CTO): "I actually really liked how the dashboard shows everything at a glance"

### Task 2: Share a report link with a stakeholder

- **Completion rate:** 69%
- **Average time:** 143s
- **Errors observed:** 2
- **Participant observations:**
  - Marcus Johnson (Engineering Director): "The notifications are just noise at this point, I ignore all of them"
  - Derek Washington (CTO): "The mobile app crashes at least once a day when I try to upload photos"
  - Omar Hassan (Product Owner): "It sends me way too many email notifications and I can't figure out how to turn them off individually"
  - Priya Patel (UX Designer): "The drag-and-drop interface is really satisfying when it works, but sometimes items just snap to the wrong place"

### Task 3: Create a chart from exported data within the app

- **Completion rate:** 89%
- **Average time:** 147s
- **Errors observed:** 1
- **Participant observations:**
  - Priya Patel (UX Designer): "The permissions system is so confusing that we just give everyone admin access"
  - Omar Hassan (Product Owner): "The search bar basically never returns what I'm actually looking for"

### Task 4: Generate a monthly summary report

- **Completion rate:** 100%
- **Average time:** 46s
- **Errors observed:** 0
- **Participant observations:**
  - Marcus Johnson (Engineering Director): "I have no idea what half the icons in the toolbar mean"
  - David Okonkwo (VP of Product): "I genuinely look forward to using the analytics view, it's the best-designed part of the product"
  - Omar Hassan (Product Owner): "Once I got the hang of it, the workflow felt pretty natural"
  - Zainab Osei (UX Researcher): "I use it every single day, so even small annoyances add up over time"

### Task 5: Customize the columns included in an export

- **Completion rate:** 62%
- **Average time:** 168s
- **Errors observed:** 0
- **Participant observations:**
  - Marcus Johnson (Engineering Director): "I accidentally sent an incomplete report to a client because the save and send buttons are right next to each other"
  - Zainab Osei (UX Researcher): "I remember thinking, why is this taking so many clicks?"
  - Derek Washington (CTO): "I don't think the pricing page made it clear what I was actually getting"
  - David Okonkwo (VP of Product): "The color contrast is so low I can barely read the secondary text"

### Task 6: Export raw data as CSV

- **Completion rate:** 69%
- **Average time:** 104s
- **Errors observed:** 3
- **Participant observations:**
  - Derek Washington (CTO): "I would absolutely recommend it to my team, with a few caveats"
  - Marcus Johnson (Engineering Director): "I can never remember where the billing page is buried"
  - Zainab Osei (UX Researcher): "The file upload limit is way too small for the kind of documents we work with"

## SUS Score

**Overall SUS Score: 72 / 100** — Grade: B — Good

The system scores above the industry average (68), indicating generally acceptable usability. However, task-level analysis reveals specific areas needing improvement.

## Key Findings

1. **[Critical]** 3 out of 5 participants attempted to use the back button instead of the in-app navigation, causing loss of form state.
2. **[Major]** Users consistently hesitated before clicking the primary CTA — the label was ambiguous.
3. **[Major]** Users could not distinguish between 'Save' and 'Save & Close' — both labels were visible simultaneously.
4. **[Minor]** Inconsistent button placement across different sections confused navigation patterns.
5. **[Minor]** The modal dialog could not be dismissed with the Escape key, violating accessibility expectations.

## Recommendations

1. Add inline validation to multi-step forms to reduce error-correction cycles.
2. Increase color contrast ratios to meet WCAG AA standards across all interactive elements.
3. Conduct a follow-up A/B test comparing the current flow with a simplified alternative.

---
*Report generated from usability testing session on 2026-02-26.*
*6 participants, 6 tasks evaluated.*