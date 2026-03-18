# Usability Test Report — Notification and Alerts System

**Date:** 2026-03-02
**Product:** Patient portal and telehealth platform (HealthBridge)
**Research Goal:** Decrease notification opt-out rate from 68% to under 40%
**Participants:** 5 (Product Owner, Sales Lead, Operations Manager, Research Lead, Engineering Director)
**Methodology:** Moderated remote usability testing with think-aloud protocol

## Participants

| ID | Name | Role | Company Size | Age |
|----|------|------|-------------|-----|
| P30 | Omar Hassan | Product Owner | 200-500 | 35 |
| P04 | James O'Brien | Sales Lead | 200-500 | 38 |
| P06 | Carlos Mendoza | Operations Manager | 500-2000 | 41 |
| P14 | Naomi Tanaka | Research Lead | 500-2000 | 33 |
| P02 | Marcus Johnson | Engineering Director | 500-2000 | 45 |

## Tasks

### Task 1: Mute notifications for a specific project

- **Completion rate:** 46%
- **Average time:** 26s
- **Errors observed:** 3
- **Participant observations:**
  - Carlos Mendoza (Operations Manager): "Once I got the hang of it, the workflow felt pretty natural"
  - Naomi Tanaka (Research Lead): "We had to create a separate shared document just to explain our internal conventions because the tool doesn't support naming rules"
  - Marcus Johnson (Engineering Director): "I was pleasantly surprised by how fast the search results came back"

### Task 2: Find and modify notification preferences

- **Completion rate:** 71%
- **Average time:** 94s
- **Errors observed:** 1
- **Participant observations:**
  - Naomi Tanaka (Research Lead): "The calendar integration was the tipping point for us, we were already using it but that made it indispensable"
  - James O'Brien (Sales Lead): "I needed to train five new team members and there's no way to share my custom views with them"

### Task 3: Find the notification that triggered an email you received

- **Completion rate:** 82%
- **Average time:** 143s
- **Errors observed:** 0
- **Participant observations:**
  - Omar Hassan (Product Owner): "The automations feature was a bit overwhelming at first but once I set up a few rules it saved hours every week"
  - Carlos Mendoza (Operations Manager): "There's no confirmation dialog before archiving a project, I've done it by accident twice"
  - Naomi Tanaka (Research Lead): "I've been using it for two years and I'm still discovering features I didn't know existed"
  - James O'Brien (Sales Lead): "The onboarding tutorial was so long I just skipped it, and then I was completely lost"

### Task 4: Configure email digest frequency

- **Completion rate:** 53%
- **Average time:** 92s
- **Errors observed:** 1
- **Participant observations:**
  - James O'Brien (Sales Lead): "The automations feature was a bit overwhelming at first but once I set up a few rules it saved hours every week"
  - Carlos Mendoza (Operations Manager): "The template library saved us weeks of setup time when we started a new client project"
  - Omar Hassan (Product Owner): "We had to create a separate shared document just to explain our internal conventions because the tool doesn't support naming rules"
  - Marcus Johnson (Engineering Director): "The onboarding wizard actually taught me things about project management I didn't know before"

### Task 5: Clear all read notifications

- **Completion rate:** 53%
- **Average time:** 138s
- **Errors observed:** 4
- **Participant observations:**
  - Naomi Tanaka (Research Lead): "The mobile app is fine for checking things, but I'd never try to do real work on it"
  - Carlos Mendoza (Operations Manager): "The error messages are completely useless, they just say something went wrong with no detail"
  - James O'Brien (Sales Lead): "Our team can't agree on the taxonomy because the tool doesn't enforce consistent labeling"
  - Marcus Johnson (Engineering Director): "We had to create a separate shared document just to explain our internal conventions because the tool doesn't support naming rules"

### Task 6: Set up a custom alert for a metric threshold

- **Completion rate:** 55%
- **Average time:** 133s
- **Errors observed:** 2
- **Participant observations:**
  - Marcus Johnson (Engineering Director): "The integration with our CI/CD pipeline means developers never have to leave the tool to update task status"
  - Omar Hassan (Product Owner): "The fact that I can't undo a bulk action makes me nervous every time I use it"
  - James O'Brien (Sales Lead): "When I collapse a section, it re-expands every time I come back to the page"
  - Naomi Tanaka (Research Lead): "The search bar basically never returns what I'm actually looking for"

## SUS Score

**Overall SUS Score: 52 / 100** — Grade: C — OK (below average for usability)

The system scores below the industry average (68), indicating significant usability concerns that should be addressed before the next release.

## Key Findings

1. **[Critical]** Error messages did not clearly indicate how to resolve the issue.
2. **[Major]** The loading state provided no progress indication, leading two participants to refresh the page.
3. **[Major]** Participants expected a drag-and-drop interaction where only click-to-select was available.
4. **[Major]** Color-coding alone was used to indicate status — problematic for color-blind users.
5. **[Minor]** The modal dialog could not be dismissed with the Escape key, violating accessibility expectations.
6. **[Cosmetic]** The active tab indicator had insufficient contrast against the background.

## Recommendations

1. Conduct a follow-up A/B test comparing the current flow with a simplified alternative.
2. Increase color contrast ratios to meet WCAG AA standards across all interactive elements.
3. Improve empty states with actionable guidance to reduce user confusion on first use.
4. Implement progressive disclosure to reduce initial cognitive load on complex screens.

---
*Report generated from usability testing session on 2026-03-02.*
*5 participants, 6 tasks evaluated.*