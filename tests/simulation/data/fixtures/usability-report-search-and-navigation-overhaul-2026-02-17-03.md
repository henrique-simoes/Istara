# Usability Test Report — Search and Navigation Overhaul

**Date:** 2026-02-17
**Product:** Patient portal and telehealth platform (HealthBridge)
**Research Goal:** Reduce support tickets related to 'can't find feature' by 35%
**Participants:** 5 (Project Manager, Product Manager, Frontend Developer, QA Engineer, DevOps Lead)
**Methodology:** Moderated remote usability testing with think-aloud protocol

## Participants

| ID | Name | Role | Company Size | Age |
|----|------|------|-------------|-----|
| P13 | Tomás García | Project Manager | 200-500 | 39 |
| P01 | Sarah Chen | Product Manager | 50-200 | 32 |
| P12 | Sofia Rossi | Frontend Developer | 50-200 | 27 |
| P16 | Fatima Al-Hassan | QA Engineer | 200-500 | 30 |
| P25 | Pavel Volkov | DevOps Lead | 200-500 | 40 |

## Tasks

### Task 1: Navigate to account settings from the home page

- **Completion rate:** 61%
- **Average time:** 41s
- **Errors observed:** 1
- **Participant observations:**
  - Sofia Rossi (Frontend Developer): "It sends me way too many email notifications and I can't figure out how to turn them off individually"
  - Tomás García (Project Manager): "The help docs are always out of date and show screenshots from an older version"
  - Fatima Al-Hassan (QA Engineer): "There's no keyboard shortcut for the one action I do fifty times a day"

### Task 2: Locate the help documentation for a feature

- **Completion rate:** 62%
- **Average time:** 61s
- **Errors observed:** 3
- **Participant observations:**
  - Sofia Rossi (Frontend Developer): "I have no idea what half the icons in the toolbar mean"
  - Fatima Al-Hassan (QA Engineer): "I tried to set up the integration with Slack three times and it failed silently each time"

### Task 3: Find a specific project using the search bar

- **Completion rate:** 82%
- **Average time:** 38s
- **Errors observed:** 0
- **Participant observations:**
  - Pavel Volkov (DevOps Lead): "Setting up the integration was a breeze, probably the smoothest part of the whole experience"
  - Sofia Rossi (Frontend Developer): "I ended up asking a coworker to walk me through it because the help docs didn't make sense"

### Task 4: Navigate to a deeply nested settings page

- **Completion rate:** 52%
- **Average time:** 71s
- **Errors observed:** 1
- **Participant observations:**
  - Sarah Chen (Product Manager): "The onboarding tutorial was so long I just skipped it, and then I was completely lost"
  - Pavel Volkov (DevOps Lead): "I genuinely look forward to using the analytics view, it's the best-designed part of the product"

### Task 5: Find a recently accessed item without using search

- **Completion rate:** 67%
- **Average time:** 93s
- **Errors observed:** 0
- **Participant observations:**
  - Tomás García (Project Manager): "The loading time is really frustrating, especially when I'm trying to pull up something in a meeting"
  - Sarah Chen (Product Manager): "I was pleasantly surprised by how fast the search results came back"
  - Fatima Al-Hassan (QA Engineer): "It does what I need about eighty percent of the time, the other twenty percent I work around"
  - Sofia Rossi (Frontend Developer): "It took me way too long to figure out how to invite my team"

### Task 6: Use the breadcrumb trail to return to a previous page

- **Completion rate:** 98%
- **Average time:** 52s
- **Errors observed:** 0
- **Participant observations:**
  - Tomás García (Project Manager): "I ended up asking a coworker to walk me through it because the help docs didn't make sense"
  - Sofia Rossi (Frontend Developer): "I had to watch a YouTube tutorial to understand the reporting feature, and that shouldn't be necessary"

## SUS Score

**Overall SUS Score: 63 / 100** — Grade: C — OK (below average for usability)

The system scores below the industry average (68), indicating significant usability concerns that should be addressed before the next release.

## Key Findings

1. **[Major]** The loading state provided no progress indication, leading two participants to refresh the page.
2. **[Major]** Form validation only triggered on submit, not inline, causing repeated correction cycles.
3. **[Major]** Participants expected a drag-and-drop interaction where only click-to-select was available.
4. **[Minor]** The tooltip text was truncated on smaller screens, hiding critical information.
5. **[Minor]** The modal dialog could not be dismissed with the Escape key, violating accessibility expectations.
6. **[Minor]** The empty state provided no guidance on how to get started.

## Recommendations

1. Conduct a follow-up A/B test comparing the current flow with a simplified alternative.
2. Add a persistent breadcrumb trail that updates in real time during multi-step flows.
3. Increase color contrast ratios to meet WCAG AA standards across all interactive elements.
4. Review and consolidate notification preferences into a single, well-organized settings page.

---
*Report generated from usability testing session on 2026-02-17.*
*5 participants, 6 tasks evaluated.*