# Usability Test Report — Mobile Experience Audit

**Date:** 2026-02-14
**Product:** Collaborative learning management system (EduVerse)
**Research Goal:** Understand why mobile session duration is 60% shorter than desktop
**Participants:** 6 (VP of Product, Mobile Developer, QA Engineer, DevOps Lead, Scrum Master, UX Researcher)
**Methodology:** Moderated remote usability testing with think-aloud protocol

## Participants

| ID | Name | Role | Company Size | Age |
|----|------|------|-------------|-----|
| P11 | David Okonkwo | VP of Product | 500-2000 | 48 |
| P28 | Yuki Sato | Mobile Developer | 10-50 | 28 |
| P16 | Fatima Al-Hassan | QA Engineer | 200-500 | 30 |
| P25 | Pavel Volkov | DevOps Lead | 200-500 | 40 |
| P26 | Lisa Johansson | Scrum Master | 500-2000 | 33 |
| P24 | Zainab Osei | UX Researcher | 50-200 | 24 |

## Tasks

### Task 1: Switch between projects using the mobile navigation

- **Completion rate:** 40%
- **Average time:** 125s
- **Errors observed:** 0
- **Participant observations:**
  - Zainab Osei (UX Researcher): "The session timeout is too short, I step away for ten minutes and have to log in again"
  - Yuki Sato (Mobile Developer): "The session timeout is too short, I step away for ten minutes and have to log in again"
  - Fatima Al-Hassan (QA Engineer): "The import feature claimed it succeeded but half the data was silently dropped"

### Task 2: Log in and navigate to the main dashboard on mobile

- **Completion rate:** 50%
- **Average time:** 33s
- **Errors observed:** 1
- **Participant observations:**
  - Fatima Al-Hassan (QA Engineer): "I'm not sure who decided the default view should show everything, it's completely overwhelming"
  - Yuki Sato (Mobile Developer): "I appreciate that they don't spam me with upgrade prompts, the free tier is genuinely useful"
  - Lisa Johansson (Scrum Master): "The fact that I can't undo a bulk action makes me nervous every time I use it"

### Task 3: Complete a multi-step form on mobile

- **Completion rate:** 95%
- **Average time:** 153s
- **Errors observed:** 1
- **Participant observations:**
  - David Okonkwo (VP of Product): "The fact that I can't undo a bulk action makes me nervous every time I use it"
  - Pavel Volkov (DevOps Lead): "The dropdown menus close if my cursor drifts even slightly outside the boundary"
  - Zainab Osei (UX Researcher): "The comment threading doesn't work properly, replies sometimes appear out of order"

### Task 4: Search for a specific item on mobile

- **Completion rate:** 84%
- **Average time:** 110s
- **Errors observed:** 0
- **Participant observations:**
  - Fatima Al-Hassan (QA Engineer): "The onboarding tutorial was so long I just skipped it, and then I was completely lost"
  - Pavel Volkov (DevOps Lead): "The audit log is essential for our compliance requirements, it tracks every change automatically"
  - David Okonkwo (VP of Product): "The way it handles recurring tasks is finally how I always thought it should work in other tools"

### Task 5: Create a new task using only the mobile interface

- **Completion rate:** 68%
- **Average time:** 110s
- **Errors observed:** 3
- **Participant observations:**
  - Yuki Sato (Mobile Developer): "Our team adopted it in about two days, which is really fast compared to other tools we've tried"
  - Zainab Osei (UX Researcher): "I think the biggest improvement they could make is better exporting, the current PDF export is basic"
  - David Okonkwo (VP of Product): "The session timeout is too short, I step away for ten minutes and have to log in again"

### Task 6: View and respond to a notification on mobile

- **Completion rate:** 42%
- **Average time:** 52s
- **Errors observed:** 2
- **Participant observations:**
  - Zainab Osei (UX Researcher): "The tool shows me information I don't have permission to act on, which is confusing"
  - Yuki Sato (Mobile Developer): "I can't attach more than one file at a time, so uploading ten documents takes forever"
  - David Okonkwo (VP of Product): "The tool shows me information I don't have permission to act on, which is confusing"
  - Pavel Volkov (DevOps Lead): "The table sort only works on one column at a time and doesn't remember my preference"

## SUS Score

**Overall SUS Score: 54 / 100** — Grade: C — OK (below average for usability)

The system scores below the industry average (68), indicating significant usability concerns that should be addressed before the next release.

## Key Findings

1. **[Critical]** Participants missed critical information below the fold — no visual cue indicated more content.
2. **[Critical]** Icon-only buttons lacked labels, and 4 of 5 participants could not identify their function.
3. **[Major]** Users consistently hesitated before clicking the primary CTA — the label was ambiguous.
4. **[Major]** Users could not distinguish between 'Save' and 'Save & Close' — both labels were visible simultaneously.
5. **[Minor]** The success confirmation message disappeared too quickly for most participants to read.
6. **[Minor]** The tooltip text was truncated on smaller screens, hiding critical information.
7. **[Cosmetic]** The active tab indicator had insufficient contrast against the background.

## Recommendations

1. Increase color contrast ratios to meet WCAG AA standards across all interactive elements.
2. Add a persistent breadcrumb trail that updates in real time during multi-step flows.
3. Provide clearer loading and progress indicators for operations exceeding 2 seconds.
4. Add inline validation to multi-step forms to reduce error-correction cycles.

---
*Report generated from usability testing session on 2026-02-14.*
*6 participants, 6 tasks evaluated.*