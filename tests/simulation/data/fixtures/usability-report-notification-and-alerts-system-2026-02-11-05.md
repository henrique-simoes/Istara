# Usability Test Report — Notification and Alerts System

**Date:** 2026-02-11
**Product:** Collaborative learning management system (EduVerse)
**Research Goal:** Decrease notification opt-out rate from 68% to under 40%
**Participants:** 5 (Engineering Director, Customer Success Lead, Product Manager, QA Engineer, Operations Manager)
**Methodology:** Moderated remote usability testing with think-aloud protocol

## Participants

| ID | Name | Role | Company Size | Age |
|----|------|------|-------------|-----|
| P02 | Marcus Johnson | Engineering Director | 500-2000 | 45 |
| P07 | Emily Watson | Customer Success Lead | 200-500 | 34 |
| P01 | Sarah Chen | Product Manager | 50-200 | 32 |
| P16 | Fatima Al-Hassan | QA Engineer | 200-500 | 30 |
| P06 | Carlos Mendoza | Operations Manager | 500-2000 | 41 |

## Tasks

### Task 1: Mute notifications for a specific project

- **Completion rate:** 50%
- **Average time:** 136s
- **Errors observed:** 1
- **Participant observations:**
  - Emily Watson (Customer Success Lead): "The date picker doesn't let me type a date manually, I have to click through months one by one"
  - Marcus Johnson (Engineering Director): "It took me two weeks to realize there was a bulk edit feature hidden in a dropdown"
  - Carlos Mendoza (Operations Manager): "When I share a link with my team, they always have to log in again even if they already have accounts"

### Task 2: Clear all read notifications

- **Completion rate:** 90%
- **Average time:** 143s
- **Errors observed:** 0
- **Participant observations:**
  - Fatima Al-Hassan (QA Engineer): "I can't customize the columns in the table view, so I'm always scrolling sideways to find what I need"
  - Carlos Mendoza (Operations Manager): "There's no keyboard shortcut for the one action I do fifty times a day"
  - Emily Watson (Customer Success Lead): "Switching between projects is painfully slow, there's no quick switcher"

### Task 3: Set up a custom alert for a metric threshold

- **Completion rate:** 97%
- **Average time:** 121s
- **Errors observed:** 0
- **Participant observations:**
  - Fatima Al-Hassan (QA Engineer): "When I saw the new design, my first reaction was, where did everything go?"
  - Sarah Chen (Product Manager): "I love the keyboard shortcuts, they save me so much time"

### Task 4: Find and modify notification preferences

- **Completion rate:** 45%
- **Average time:** 49s
- **Errors observed:** 3
- **Participant observations:**
  - Marcus Johnson (Engineering Director): "The file upload limit is way too small for the kind of documents we work with"
  - Fatima Al-Hassan (QA Engineer): "Honestly, I almost gave up during the sign-up process"
  - Emily Watson (Customer Success Lead): "Once I got the hang of it, the workflow felt pretty natural"
  - Carlos Mendoza (Operations Manager): "The dashboard widgets rearrange themselves every time I log in, which is disorienting"

### Task 5: Configure email digest frequency

- **Completion rate:** 83%
- **Average time:** 54s
- **Errors observed:** 0
- **Participant observations:**
  - Emily Watson (Customer Success Lead): "I actually really liked how the dashboard shows everything at a glance"
  - Fatima Al-Hassan (QA Engineer): "I love the keyboard shortcuts, they save me so much time"
  - Sarah Chen (Product Manager): "The permissions system is so confusing that we just give everyone admin access"
  - Carlos Mendoza (Operations Manager): "There's no keyboard shortcut for the one action I do fifty times a day"

### Task 6: Distinguish between urgent and non-urgent notifications

- **Completion rate:** 62%
- **Average time:** 45s
- **Errors observed:** 1
- **Participant observations:**
  - Marcus Johnson (Engineering Director): "The fact that I can't undo a bulk action makes me nervous every time I use it"
  - Sarah Chen (Product Manager): "I actually really liked how the dashboard shows everything at a glance"
  - Emily Watson (Customer Success Lead): "When I saw the new design, my first reaction was, where did everything go?"
  - Carlos Mendoza (Operations Manager): "I had to watch a YouTube tutorial to understand the reporting feature, and that shouldn't be necessary"

## SUS Score

**Overall SUS Score: 66 / 100** — Grade: C — OK (below average for usability)

The system scores below the industry average (68), indicating significant usability concerns that should be addressed before the next release.

## Key Findings

1. **[Major]** Form validation only triggered on submit, not inline, causing repeated correction cycles.
2. **[Major]** The loading state provided no progress indication, leading two participants to refresh the page.
3. **[Major]** Users could not distinguish between 'Save' and 'Save & Close' — both labels were visible simultaneously.
4. **[Major]** Users consistently hesitated before clicking the primary CTA — the label was ambiguous.

## Recommendations

1. Increase color contrast ratios to meet WCAG AA standards across all interactive elements.
2. Provide clearer loading and progress indicators for operations exceeding 2 seconds.
3. Improve empty states with actionable guidance to reduce user confusion on first use.
4. Implement progressive disclosure to reduce initial cognitive load on complex screens.

---
*Report generated from usability testing session on 2026-02-11.*
*5 participants, 6 tasks evaluated.*