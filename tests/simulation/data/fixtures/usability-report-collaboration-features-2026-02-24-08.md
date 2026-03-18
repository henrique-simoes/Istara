# Usability Test Report — Collaboration Features

**Date:** 2026-02-24
**Product:** Project management platform (TechStart Inc)
**Research Goal:** Increase team workspace adoption from 23% to 50% of active accounts
**Participants:** 5 (Product Manager, Engineering Director, Content Strategist, Frontend Developer, Solutions Architect)
**Methodology:** Moderated remote usability testing with think-aloud protocol

## Participants

| ID | Name | Role | Company Size | Age |
|----|------|------|-------------|-----|
| P01 | Sarah Chen | Product Manager | 50-200 | 32 |
| P02 | Marcus Johnson | Engineering Director | 500-2000 | 45 |
| P22 | Hannah Eriksson | Content Strategist | 10-50 | 35 |
| P12 | Sofia Rossi | Frontend Developer | 50-200 | 27 |
| P19 | Andre Baptiste | Solutions Architect | 500-2000 | 37 |

## Tasks

### Task 1: Create a shared workspace and invite collaborators

- **Completion rate:** 55%
- **Average time:** 120s
- **Errors observed:** 3
- **Participant observations:**
  - Hannah Eriksson (Content Strategist): "There's no way to see a chronological history of changes to a single task"
  - Sarah Chen (Product Manager): "It takes six clicks to do something that should be a right-click context menu action"

### Task 2: Leave a comment on a shared artifact

- **Completion rate:** 48%
- **Average time:** 130s
- **Errors observed:** 1
- **Participant observations:**
  - Sarah Chen (Product Manager): "I use it every single day, so even small annoyances add up over time"
  - Sofia Rossi (Frontend Developer): "The session timeout is too short, I step away for ten minutes and have to log in again"

### Task 3: Set permissions on a shared folder

- **Completion rate:** 69%
- **Average time:** 98s
- **Errors observed:** 0
- **Participant observations:**
  - Sarah Chen (Product Manager): "I accidentally deleted a project and there was no way to undo it"
  - Marcus Johnson (Engineering Director): "The link previews don't work for internal pages, so shared links are just cryptic URLs"
  - Hannah Eriksson (Content Strategist): "I genuinely enjoy the weekly summary it generates, it's surprisingly insightful for an automated report"

### Task 4: Assign a task to another team member

- **Completion rate:** 59%
- **Average time:** 130s
- **Errors observed:** 3
- **Participant observations:**
  - Andre Baptiste (Solutions Architect): "It's the first tool where I actually trust the automated suggestions because they're contextually relevant"
  - Sofia Rossi (Frontend Developer): "It feels like it was designed by engineers for engineers, not for someone like me"
  - Sarah Chen (Product Manager): "I can create a complete project plan in about twenty minutes that would have taken me half a day before"

### Task 5: View and resolve a comment thread

- **Completion rate:** 86%
- **Average time:** 96s
- **Errors observed:** 0
- **Participant observations:**
  - Andre Baptiste (Solutions Architect): "The activity feed gives me a clear picture of what happened while I was away without reading every message"
  - Hannah Eriksson (Content Strategist): "The print view is unusable, it cuts off text and doesn't paginate properly"
  - Marcus Johnson (Engineering Director): "I used to spend my Monday mornings organizing my week, now the tool basically does it for me"
  - Sarah Chen (Product Manager): "It sends me way too many email notifications and I can't figure out how to turn them off individually"

### Task 6: Share a document with a specific team member

- **Completion rate:** 93%
- **Average time:** 149s
- **Errors observed:** 0
- **Participant observations:**
  - Hannah Eriksson (Content Strategist): "I've been using it for two years and I'm still discovering features I didn't know existed"
  - Sofia Rossi (Frontend Developer): "When I collapse a section, it re-expands every time I come back to the page"
  - Andre Baptiste (Solutions Architect): "Switching between projects is painfully slow, there's no quick switcher"

## SUS Score

**Overall SUS Score: 60 / 100** — Grade: C — OK (below average for usability)

The system scores below the industry average (68), indicating significant usability concerns that should be addressed before the next release.

## Key Findings

1. **[Critical]** Icon-only buttons lacked labels, and 4 of 5 participants could not identify their function.
2. **[Critical]** 3 out of 5 participants attempted to use the back button instead of the in-app navigation, causing loss of form state.
3. **[Major]** The loading state provided no progress indication, leading two participants to refresh the page.
4. **[Major]** Auto-complete suggestions in the search bar were irrelevant for the top 3 most common queries.
5. **[Minor]** The success confirmation message disappeared too quickly for most participants to read.
6. **[Minor]** The tooltip text was truncated on smaller screens, hiding critical information.
7. **[Minor]** Inconsistent button placement across different sections confused navigation patterns.

## Recommendations

1. Implement progressive disclosure to reduce initial cognitive load on complex screens.
2. Conduct a follow-up A/B test comparing the current flow with a simplified alternative.
3. Add inline validation to multi-step forms to reduce error-correction cycles.
4. Improve empty states with actionable guidance to reduce user confusion on first use.

---
*Report generated from usability testing session on 2026-02-24.*
*5 participants, 6 tasks evaluated.*