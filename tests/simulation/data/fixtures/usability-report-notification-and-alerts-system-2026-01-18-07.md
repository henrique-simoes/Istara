# Usability Test Report — Notification and Alerts System

**Date:** 2026-01-18
**Product:** Patient portal and telehealth platform (HealthBridge)
**Research Goal:** Decrease notification opt-out rate from 68% to under 40%
**Participants:** 7 (Support Specialist, Solutions Architect, Junior Developer, Sales Lead, Business Analyst, Frontend Developer, Scrum Master)
**Methodology:** Moderated remote usability testing with think-aloud protocol

## Participants

| ID | Name | Role | Company Size | Age |
|----|------|------|-------------|-----|
| P17 | Liam Murphy | Support Specialist | 50-200 | 25 |
| P19 | Andre Baptiste | Solutions Architect | 500-2000 | 37 |
| P05 | Aisha Rahman | Junior Developer | 50-200 | 26 |
| P04 | James O'Brien | Sales Lead | 200-500 | 38 |
| P27 | Kwame Asante | Business Analyst | 2000+ | 31 |
| P12 | Sofia Rossi | Frontend Developer | 50-200 | 27 |
| P26 | Lisa Johansson | Scrum Master | 500-2000 | 33 |

## Tasks

### Task 1: Distinguish between urgent and non-urgent notifications

- **Completion rate:** 73%
- **Average time:** 140s
- **Errors observed:** 0
- **Participant observations:**
  - Andre Baptiste (Solutions Architect): "Setting up the integration was a breeze, probably the smoothest part of the whole experience"
  - James O'Brien (Sales Lead): "The help docs are always out of date and show screenshots from an older version"

### Task 2: Mute notifications for a specific project

- **Completion rate:** 96%
- **Average time:** 71s
- **Errors observed:** 1
- **Participant observations:**
  - Andre Baptiste (Solutions Architect): "The onboarding emails were genuinely helpful, they came at the right pace"
  - Lisa Johansson (Scrum Master): "It took me way too long to figure out how to invite my team"
  - Liam Murphy (Support Specialist): "The notifications are just noise at this point, I ignore all of them"

### Task 3: Configure email digest frequency

- **Completion rate:** 83%
- **Average time:** 132s
- **Errors observed:** 1
- **Participant observations:**
  - Liam Murphy (Support Specialist): "I can't customize the columns in the table view, so I'm always scrolling sideways to find what I need"
  - Andre Baptiste (Solutions Architect): "I was pleasantly surprised by how fast the search results came back"
  - Aisha Rahman (Junior Developer): "My manager asked me to pull a report and it took me forty-five minutes to figure out how"

### Task 4: Clear all read notifications

- **Completion rate:** 60%
- **Average time:** 145s
- **Errors observed:** 1
- **Participant observations:**
  - Kwame Asante (Business Analyst): "It took me way too long to figure out how to invite my team"
  - James O'Brien (Sales Lead): "I would absolutely recommend it to my team, with a few caveats"
  - Aisha Rahman (Junior Developer): "I can never remember where the billing page is buried"
  - Sofia Rossi (Frontend Developer): "I think the biggest issue is just consistency, some parts feel modern and others feel like they haven't been updated in years"

### Task 5: Find and modify notification preferences

- **Completion rate:** 83%
- **Average time:** 53s
- **Errors observed:** 2
- **Participant observations:**
  - Lisa Johansson (Scrum Master): "I was pleasantly surprised by how fast the search results came back"
  - Andre Baptiste (Solutions Architect): "Setting up the integration was a breeze, probably the smoothest part of the whole experience"

### Task 6: Set up a custom alert for a metric threshold

- **Completion rate:** 98%
- **Average time:** 173s
- **Errors observed:** 1
- **Participant observations:**
  - Aisha Rahman (Junior Developer): "Every time I export a report, the formatting is completely off and I have to fix it in Excel"
  - Lisa Johansson (Scrum Master): "I was confused by the terminology, what you call a workspace I would call a project"
  - Liam Murphy (Support Specialist): "I can never remember where the billing page is buried"

## SUS Score

**Overall SUS Score: 79 / 100** — Grade: B — Good

The system scores above the industry average (68), indicating generally acceptable usability. However, task-level analysis reveals specific areas needing improvement.

## Key Findings

1. **[Critical]** 3 out of 5 participants attempted to use the back button instead of the in-app navigation, causing loss of form state.
2. **[Major]** The loading state provided no progress indication, leading two participants to refresh the page.
3. **[Major]** Users consistently hesitated before clicking the primary CTA — the label was ambiguous.
4. **[Major]** Auto-complete suggestions in the search bar were irrelevant for the top 3 most common queries.
5. **[Minor]** The tooltip text was truncated on smaller screens, hiding critical information.
6. **[Minor]** Inconsistent button placement across different sections confused navigation patterns.
7. **[Minor]** The success confirmation message disappeared too quickly for most participants to read.

## Recommendations

1. Review and consolidate notification preferences into a single, well-organized settings page.
2. Provide clearer loading and progress indicators for operations exceeding 2 seconds.
3. Add keyboard shortcut support for the 10 most common user actions.

---
*Report generated from usability testing session on 2026-01-18.*
*7 participants, 6 tasks evaluated.*