# Usability Test Report — Mobile Experience Audit

**Date:** 2026-02-19
**Product:** Fleet tracking and route optimization dashboard (ShipRoute Global)
**Research Goal:** Understand why mobile session duration is 60% shorter than desktop
**Participants:** 8 (VP of Product, CTO, Content Strategist, Product Owner, Product Designer, Product Manager, Account Executive, Customer Success Lead)
**Methodology:** Moderated remote usability testing with think-aloud protocol

## Participants

| ID | Name | Role | Company Size | Age |
|----|------|------|-------------|-----|
| P11 | David Okonkwo | VP of Product | 500-2000 | 48 |
| P15 | Derek Washington | CTO | 10-50 | 52 |
| P22 | Hannah Eriksson | Content Strategist | 10-50 | 35 |
| P30 | Omar Hassan | Product Owner | 200-500 | 35 |
| P20 | Jessica Nguyen | Product Designer | 50-200 | 29 |
| P01 | Sarah Chen | Product Manager | 50-200 | 32 |
| P23 | Michael Torres | Account Executive | 500-2000 | 46 |
| P07 | Emily Watson | Customer Success Lead | 200-500 | 34 |

## Tasks

### Task 1: Switch between projects using the mobile navigation

- **Completion rate:** 69%
- **Average time:** 68s
- **Errors observed:** 3
- **Participant observations:**
  - Jessica Nguyen (Product Designer): "When I saw the new design, my first reaction was, where did everything go?"
  - Michael Torres (Account Executive): "I keep a sticky note on my monitor with the steps to do the export because it's not intuitive at all"

### Task 2: Upload a photo attachment from the camera roll

- **Completion rate:** 43%
- **Average time:** 113s
- **Errors observed:** 3
- **Participant observations:**
  - Emily Watson (Customer Success Lead): "The search bar basically never returns what I'm actually looking for"
  - Omar Hassan (Product Owner): "Switching between projects is painfully slow, there's no quick switcher"

### Task 3: Create a new task using only the mobile interface

- **Completion rate:** 85%
- **Average time:** 112s
- **Errors observed:** 1
- **Participant observations:**
  - Michael Torres (Account Executive): "The loading time is really frustrating, especially when I'm trying to pull up something in a meeting"
  - Jessica Nguyen (Product Designer): "The dashboard widgets rearrange themselves every time I log in, which is disorienting"

### Task 4: View and respond to a notification on mobile

- **Completion rate:** 48%
- **Average time:** 67s
- **Errors observed:** 0
- **Participant observations:**
  - Sarah Chen (Product Manager): "I can never remember where the billing page is buried"
  - David Okonkwo (VP of Product): "I use it every single day, so even small annoyances add up over time"
  - Derek Washington (CTO): "Every time I export a report, the formatting is completely off and I have to fix it in Excel"

### Task 5: Log in and navigate to the main dashboard on mobile

- **Completion rate:** 52%
- **Average time:** 148s
- **Errors observed:** 2
- **Participant observations:**
  - Derek Washington (CTO): "There's no keyboard shortcut for the one action I do fifty times a day"
  - Omar Hassan (Product Owner): "I accidentally sent an incomplete report to a client because the save and send buttons are right next to each other"

### Task 6: Complete a multi-step form on mobile

- **Completion rate:** 53%
- **Average time:** 70s
- **Errors observed:** 4
- **Participant observations:**
  - Michael Torres (Account Executive): "Compared to what we used before, this is a huge improvement, but the bar was pretty low"
  - Omar Hassan (Product Owner): "I think the biggest issue is just consistency, some parts feel modern and others feel like they haven't been updated in years"
  - Emily Watson (Customer Success Lead): "The notifications are just noise at this point, I ignore all of them"

## SUS Score

**Overall SUS Score: 56 / 100** — Grade: C — OK (below average for usability)

The system scores below the industry average (68), indicating significant usability concerns that should be addressed before the next release.

## Key Findings

1. **[Critical]** 3 out of 5 participants attempted to use the back button instead of the in-app navigation, causing loss of form state.
2. **[Major]** Users could not distinguish between 'Save' and 'Save & Close' — both labels were visible simultaneously.
3. **[Minor]** The modal dialog could not be dismissed with the Escape key, violating accessibility expectations.
4. **[Cosmetic]** Font size in the data table was too small for comfortable reading during extended use.
5. **[Cosmetic]** The active tab indicator had insufficient contrast against the background.

## Recommendations

1. Add inline validation to multi-step forms to reduce error-correction cycles.
2. Improve empty states with actionable guidance to reduce user confusion on first use.
3. Provide clearer loading and progress indicators for operations exceeding 2 seconds.
4. Conduct a follow-up A/B test comparing the current flow with a simplified alternative.
5. Review and consolidate notification preferences into a single, well-organized settings page.

---
*Report generated from usability testing session on 2026-02-19.*
*8 participants, 6 tasks evaluated.*