# Usability Test Report — Notification and Alerts System

**Date:** 2026-02-20
**Product:** Collaborative learning management system (EduVerse)
**Research Goal:** Decrease notification opt-out rate from 68% to under 40%
**Participants:** 5 (UX Designer, Business Analyst, IT Administrator, Content Strategist, Product Designer)
**Methodology:** Moderated remote usability testing with think-aloud protocol

## Participants

| ID | Name | Role | Company Size | Age |
|----|------|------|-------------|-----|
| P03 | Priya Patel | UX Designer | 10-50 | 28 |
| P27 | Kwame Asante | Business Analyst | 2000+ | 31 |
| P09 | Oluwaseun Adeyemi | IT Administrator | 2000+ | 36 |
| P22 | Hannah Eriksson | Content Strategist | 10-50 | 35 |
| P20 | Jessica Nguyen | Product Designer | 50-200 | 29 |

## Tasks

### Task 1: Configure email digest frequency

- **Completion rate:** 52%
- **Average time:** 47s
- **Errors observed:** 1
- **Participant observations:**
  - Kwame Asante (Business Analyst): "I don't think the pricing page made it clear what I was actually getting"
  - Hannah Eriksson (Content Strategist): "The help docs are always out of date and show screenshots from an older version"

### Task 2: Mute notifications for a specific project

- **Completion rate:** 63%
- **Average time:** 41s
- **Errors observed:** 2
- **Participant observations:**
  - Kwame Asante (Business Analyst): "It feels like it was designed by engineers for engineers, not for someone like me"
  - Priya Patel (UX Designer): "The error messages are completely useless, they just say something went wrong with no detail"
  - Hannah Eriksson (Content Strategist): "The date picker doesn't let me type a date manually, I have to click through months one by one"

### Task 3: Distinguish between urgent and non-urgent notifications

- **Completion rate:** 80%
- **Average time:** 81s
- **Errors observed:** 1
- **Participant observations:**
  - Kwame Asante (Business Analyst): "It's one of those tools where you know the feature exists, you just can't find it"
  - Jessica Nguyen (Product Designer): "I love the keyboard shortcuts, they save me so much time"

### Task 4: Find and modify notification preferences

- **Completion rate:** 63%
- **Average time:** 81s
- **Errors observed:** 1
- **Participant observations:**
  - Kwame Asante (Business Analyst): "Compared to what we used before, this is a huge improvement, but the bar was pretty low"
  - Priya Patel (UX Designer): "It feels like it was designed by engineers for engineers, not for someone like me"

### Task 5: Clear all read notifications

- **Completion rate:** 69%
- **Average time:** 161s
- **Errors observed:** 1
- **Participant observations:**
  - Hannah Eriksson (Content Strategist): "I use it every single day, so even small annoyances add up over time"
  - Kwame Asante (Business Analyst): "The notifications are just noise at this point, I ignore all of them"
  - Oluwaseun Adeyemi (IT Administrator): "It's one of those tools where you know the feature exists, you just can't find it"
  - Priya Patel (UX Designer): "There's no keyboard shortcut for the one action I do fifty times a day"

### Task 6: Find the notification that triggered an email you received

- **Completion rate:** 58%
- **Average time:** 73s
- **Errors observed:** 3
- **Participant observations:**
  - Hannah Eriksson (Content Strategist): "I couldn't find where to change my settings, I ended up Googling it"
  - Priya Patel (UX Designer): "There's no keyboard shortcut for the one action I do fifty times a day"
  - Kwame Asante (Business Analyst): "It feels like it was designed by engineers for engineers, not for someone like me"
  - Jessica Nguyen (Product Designer): "Setting up the integration was a breeze, probably the smoothest part of the whole experience"

## SUS Score

**Overall SUS Score: 67 / 100** — Grade: C — OK (below average for usability)

The system scores below the industry average (68), indicating significant usability concerns that should be addressed before the next release.

## Key Findings

1. **[Major]** The loading state provided no progress indication, leading two participants to refresh the page.
2. **[Major]** Form validation only triggered on submit, not inline, causing repeated correction cycles.
3. **[Minor]** The success confirmation message disappeared too quickly for most participants to read.
4. **[Minor]** The empty state provided no guidance on how to get started.
5. **[Minor]** The breadcrumb trail did not update after a multi-step action, leaving users disoriented.
6. **[Minor]** The tooltip text was truncated on smaller screens, hiding critical information.

## Recommendations

1. Implement progressive disclosure to reduce initial cognitive load on complex screens.
2. Increase color contrast ratios to meet WCAG AA standards across all interactive elements.
3. Conduct a follow-up A/B test comparing the current flow with a simplified alternative.
4. Add keyboard shortcut support for the 10 most common user actions.

---
*Report generated from usability testing session on 2026-02-20.*
*5 participants, 6 tasks evaluated.*