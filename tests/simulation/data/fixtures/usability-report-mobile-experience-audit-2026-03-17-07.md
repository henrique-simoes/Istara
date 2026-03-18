# Usability Test Report — Mobile Experience Audit

**Date:** 2026-03-17
**Product:** Collaborative learning management system (EduVerse)
**Research Goal:** Understand why mobile session duration is 60% shorter than desktop
**Participants:** 7 (Mobile Developer, Content Strategist, Product Manager, Data Analyst, Head of Training, Research Lead, Engineering Director)
**Methodology:** Moderated remote usability testing with think-aloud protocol

## Participants

| ID | Name | Role | Company Size | Age |
|----|------|------|-------------|-----|
| P28 | Yuki Sato | Mobile Developer | 10-50 | 28 |
| P22 | Hannah Eriksson | Content Strategist | 10-50 | 35 |
| P01 | Sarah Chen | Product Manager | 50-200 | 32 |
| P08 | Wei Zhang | Data Analyst | 50-200 | 29 |
| P29 | Catherine Dubois | Head of Training | 2000+ | 50 |
| P14 | Naomi Tanaka | Research Lead | 500-2000 | 33 |
| P02 | Marcus Johnson | Engineering Director | 500-2000 | 45 |

## Tasks

### Task 1: Upload a photo attachment from the camera roll

- **Completion rate:** 91%
- **Average time:** 25s
- **Errors observed:** 0
- **Participant observations:**
  - Sarah Chen (Product Manager): "The print view is unusable, it cuts off text and doesn't paginate properly"
  - Wei Zhang (Data Analyst): "The error messages are completely useless, they just say something went wrong with no detail"
  - Yuki Sato (Mobile Developer): "The dashboard widgets rearrange themselves every time I log in, which is disorienting"

### Task 2: Log in and navigate to the main dashboard on mobile

- **Completion rate:** 51%
- **Average time:** 140s
- **Errors observed:** 0
- **Participant observations:**
  - Wei Zhang (Data Analyst): "There's a loading spinner that appears for every tiny interaction and it makes the tool feel sluggish"
  - Marcus Johnson (Engineering Director): "The dashboard widgets rearrange themselves every time I log in, which is disorienting"
  - Yuki Sato (Mobile Developer): "I love the keyboard shortcuts, they save me so much time"

### Task 3: Switch between projects using the mobile navigation

- **Completion rate:** 90%
- **Average time:** 112s
- **Errors observed:** 0
- **Participant observations:**
  - Wei Zhang (Data Analyst): "The search bar basically never returns what I'm actually looking for"
  - Hannah Eriksson (Content Strategist): "I think the biggest issue is just consistency, some parts feel modern and others feel like they haven't been updated in years"
  - Yuki Sato (Mobile Developer): "The color contrast is so low I can barely read the secondary text"
  - Sarah Chen (Product Manager): "Every time there's an update, my custom workflow automations break and I have to rebuild them"

### Task 4: Search for a specific item on mobile

- **Completion rate:** 58%
- **Average time:** 20s
- **Errors observed:** 2
- **Participant observations:**
  - Sarah Chen (Product Manager): "Every time I try to copy-paste from the tool into an email, the formatting gets completely mangled"
  - Yuki Sato (Mobile Developer): "It handles large projects with hundreds of tasks without slowing down, which not every tool can claim"
  - Naomi Tanaka (Research Lead): "I tried to set up the integration with Slack three times and it failed silently each time"

### Task 5: Complete a multi-step form on mobile

- **Completion rate:** 57%
- **Average time:** 101s
- **Errors observed:** 3
- **Participant observations:**
  - Hannah Eriksson (Content Strategist): "It took me way too long to figure out how to invite my team"
  - Wei Zhang (Data Analyst): "I can't drag tasks between different project boards, so I end up duplicating them manually"

### Task 6: Create a new task using only the mobile interface

- **Completion rate:** 79%
- **Average time:** 140s
- **Errors observed:** 1
- **Participant observations:**
  - Yuki Sato (Mobile Developer): "The dashboard widgets rearrange themselves every time I log in, which is disorienting"
  - Catherine Dubois (Head of Training): "The calendar view doesn't show tasks that span multiple days correctly, they just appear on the start date"

## SUS Score

**Overall SUS Score: 60 / 100** — Grade: C — OK (below average for usability)

The system scores below the industry average (68), indicating significant usability concerns that should be addressed before the next release.

## Key Findings

1. **[Major]** Form validation only triggered on submit, not inline, causing repeated correction cycles.
2. **[Major]** The loading state provided no progress indication, leading two participants to refresh the page.
3. **[Major]** Participants expected a drag-and-drop interaction where only click-to-select was available.
4. **[Major]** Users could not distinguish between 'Save' and 'Save & Close' — both labels were visible simultaneously.
5. **[Minor]** Inconsistent button placement across different sections confused navigation patterns.

## Recommendations

1. Review and consolidate notification preferences into a single, well-organized settings page.
2. Add inline validation to multi-step forms to reduce error-correction cycles.
3. Add keyboard shortcut support for the 10 most common user actions.
4. Increase color contrast ratios to meet WCAG AA standards across all interactive elements.

---
*Report generated from usability testing session on 2026-03-17.*
*7 participants, 6 tasks evaluated.*