# Usability Test Report — Pricing Page Conversion

**Date:** 2026-01-18
**Product:** Collaborative learning management system (EduVerse)
**Research Goal:** Increase free-to-paid conversion rate from 3.1% to 5%
**Participants:** 6 (QA Engineer, Engineering Director, UX Designer, Business Analyst, Head of Training, Support Specialist)
**Methodology:** Moderated remote usability testing with think-aloud protocol

## Participants

| ID | Name | Role | Company Size | Age |
|----|------|------|-------------|-----|
| P16 | Fatima Al-Hassan | QA Engineer | 200-500 | 30 |
| P02 | Marcus Johnson | Engineering Director | 500-2000 | 45 |
| P03 | Priya Patel | UX Designer | 10-50 | 28 |
| P27 | Kwame Asante | Business Analyst | 2000+ | 31 |
| P29 | Catherine Dubois | Head of Training | 2000+ | 50 |
| P17 | Liam Murphy | Support Specialist | 50-200 | 25 |

## Tasks

### Task 1: Start a free trial from the pricing page

- **Completion rate:** 65%
- **Average time:** 163s
- **Errors observed:** 2
- **Participant observations:**
  - Kwame Asante (Business Analyst): "I'm not sure who decided the default view should show everything, it's completely overwhelming"
  - Priya Patel (UX Designer): "It does what I need about eighty percent of the time, the other twenty percent I work around"

### Task 2: Calculate the cost for your team size

- **Completion rate:** 54%
- **Average time:** 71s
- **Errors observed:** 3
- **Participant observations:**
  - Fatima Al-Hassan (QA Engineer): "The search bar basically never returns what I'm actually looking for"
  - Catherine Dubois (Head of Training): "I couldn't find where to change my settings, I ended up Googling it"
  - Marcus Johnson (Engineering Director): "I love the keyboard shortcuts, they save me so much time"

### Task 3: Compare features across pricing tiers

- **Completion rate:** 91%
- **Average time:** 33s
- **Errors observed:** 1
- **Participant observations:**
  - Priya Patel (UX Designer): "I don't think the pricing page made it clear what I was actually getting"
  - Fatima Al-Hassan (QA Engineer): "Honestly, I almost gave up during the sign-up process"
  - Catherine Dubois (Head of Training): "It's one of those tools where you know the feature exists, you just can't find it"

### Task 4: Identify which plan includes the feature you need

- **Completion rate:** 59%
- **Average time:** 67s
- **Errors observed:** 1
- **Participant observations:**
  - Fatima Al-Hassan (QA Engineer): "I use it every single day, so even small annoyances add up over time"
  - Marcus Johnson (Engineering Director): "I tried to set up the integration with Slack three times and it failed silently each time"
  - Priya Patel (UX Designer): "When I saw the new design, my first reaction was, where did everything go?"

### Task 5: Locate the enterprise contact form

- **Completion rate:** 62%
- **Average time:** 108s
- **Errors observed:** 0
- **Participant observations:**
  - Fatima Al-Hassan (QA Engineer): "It took me way too long to figure out how to invite my team"
  - Priya Patel (UX Designer): "The onboarding emails were genuinely helpful, they came at the right pace"
  - Liam Murphy (Support Specialist): "I was confused by the terminology, what you call a workspace I would call a project"

### Task 6: Find cancellation or downgrade options

- **Completion rate:** 98%
- **Average time:** 18s
- **Errors observed:** 1
- **Participant observations:**
  - Kwame Asante (Business Analyst): "I remember thinking, why is this taking so many clicks?"
  - Fatima Al-Hassan (QA Engineer): "The search bar basically never returns what I'm actually looking for"
  - Marcus Johnson (Engineering Director): "The notifications are just noise at this point, I ignore all of them"
  - Catherine Dubois (Head of Training): "The fact that I can't undo a bulk action makes me nervous every time I use it"

## SUS Score

**Overall SUS Score: 74 / 100** — Grade: B — Good

The system scores above the industry average (68), indicating generally acceptable usability. However, task-level analysis reveals specific areas needing improvement.

## Key Findings

1. **[Critical]** 3 out of 5 participants attempted to use the back button instead of the in-app navigation, causing loss of form state.
2. **[Critical]** Icon-only buttons lacked labels, and 4 of 5 participants could not identify their function.
3. **[Critical]** Error messages did not clearly indicate how to resolve the issue.
4. **[Major]** Form validation only triggered on submit, not inline, causing repeated correction cycles.
5. **[Major]** Users consistently hesitated before clicking the primary CTA — the label was ambiguous.
6. **[Major]** The loading state provided no progress indication, leading two participants to refresh the page.
7. **[Major]** Users could not distinguish between 'Save' and 'Save & Close' — both labels were visible simultaneously.

## Recommendations

1. Add inline validation to multi-step forms to reduce error-correction cycles.
2. Add visible text labels alongside icon-only buttons in the toolbar.
3. Add a persistent breadcrumb trail that updates in real time during multi-step flows.
4. Improve empty states with actionable guidance to reduce user confusion on first use.

---
*Report generated from usability testing session on 2026-01-18.*
*6 participants, 6 tasks evaluated.*