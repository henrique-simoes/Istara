# Usability Test Report — Dashboard Usability

**Date:** 2026-02-19
**Product:** Patient portal and telehealth platform (HealthBridge)
**Research Goal:** Improve time-to-insight from average 4.2 minutes to under 2 minutes
**Participants:** 6 (Engineering Manager, Frontend Developer, Data Analyst, VP of Product, Head of Training, Content Strategist)
**Methodology:** Moderated remote usability testing with think-aloud protocol

## Participants

| ID | Name | Role | Company Size | Age |
|----|------|------|-------------|-----|
| P21 | Raj Krishnamurthy | Engineering Manager | 200-500 | 42 |
| P12 | Sofia Rossi | Frontend Developer | 50-200 | 27 |
| P08 | Wei Zhang | Data Analyst | 50-200 | 29 |
| P11 | David Okonkwo | VP of Product | 500-2000 | 48 |
| P29 | Catherine Dubois | Head of Training | 2000+ | 50 |
| P22 | Hannah Eriksson | Content Strategist | 10-50 | 35 |

## Tasks

### Task 1: Locate the weekly performance summary

- **Completion rate:** 45%
- **Average time:** 77s
- **Errors observed:** 3
- **Participant observations:**
  - Hannah Eriksson (Content Strategist): "What makes it work for us is that it's flexible enough for both our engineering and marketing teams"
  - Catherine Dubois (Head of Training): "I couldn't find where to change my settings, I ended up Googling it"

### Task 2: Export the current dashboard view as PDF

- **Completion rate:** 45%
- **Average time:** 56s
- **Errors observed:** 2
- **Participant observations:**
  - Raj Krishnamurthy (Engineering Manager): "Switching between projects is painfully slow, there's no quick switcher"
  - Wei Zhang (Data Analyst): "I can tell the team that built this actually uses their own product, the little details show it"
  - Catherine Dubois (Head of Training): "I've never had a tool that actually made meetings shorter, but the shared boards did exactly that"

### Task 3: Find and pin a specific metric to the top

- **Completion rate:** 96%
- **Average time:** 126s
- **Errors observed:** 1
- **Participant observations:**
  - David Okonkwo (VP of Product): "The notifications are just noise at this point, I ignore all of them"
  - Sofia Rossi (Frontend Developer): "The calendar view doesn't show tasks that span multiple days correctly, they just appear on the start date"
  - Hannah Eriksson (Content Strategist): "The contrast between read and unread items is so subtle I can't tell them apart"
  - Raj Krishnamurthy (Engineering Manager): "The auto-save never seems to work when I need it most, I've lost entire paragraphs of notes"

### Task 4: Switch between team and personal dashboard views

- **Completion rate:** 84%
- **Average time:** 42s
- **Errors observed:** 1
- **Participant observations:**
  - Catherine Dubois (Head of Training): "The permission system is surprisingly granular, we can control exactly who sees what"
  - Raj Krishnamurthy (Engineering Manager): "I genuinely look forward to using the analytics view, it's the best-designed part of the product"
  - Sofia Rossi (Frontend Developer): "The recurring task feature creates duplicates instead of resetting the original task"
  - Wei Zhang (Data Analyst): "I think the biggest strength is how customizable the views are, everyone sets it up differently"

### Task 5: Identify the highest-performing metric this month

- **Completion rate:** 62%
- **Average time:** 124s
- **Errors observed:** 3
- **Participant observations:**
  - Hannah Eriksson (Content Strategist): "What I appreciate most is that it doesn't try to do everything, it does its core job well"
  - Wei Zhang (Data Analyst): "The autocomplete in the search field suggests results from archived projects that aren't relevant anymore"
  - David Okonkwo (VP of Product): "The loading time is really frustrating, especially when I'm trying to pull up something in a meeting"

### Task 6: Add a custom widget to the dashboard

- **Completion rate:** 93%
- **Average time:** 105s
- **Errors observed:** 1
- **Participant observations:**
  - Sofia Rossi (Frontend Developer): "There's a loading spinner that appears for every tiny interaction and it makes the tool feel sluggish"
  - David Okonkwo (VP of Product): "The API documentation is actually readable, which is rare, our developers integrated it in a day"
  - Raj Krishnamurthy (Engineering Manager): "I think the biggest issue is just consistency, some parts feel modern and others feel like they haven't been updated in years"
  - Wei Zhang (Data Analyst): "I ended up asking a coworker to walk me through it because the help docs didn't make sense"

## SUS Score

**Overall SUS Score: 72 / 100** — Grade: B — Good

The system scores above the industry average (68), indicating generally acceptable usability. However, task-level analysis reveals specific areas needing improvement.

## Key Findings

1. **[Critical]** Error messages did not clearly indicate how to resolve the issue.
2. **[Major]** Auto-complete suggestions in the search bar were irrelevant for the top 3 most common queries.
3. **[Major]** Users could not distinguish between 'Save' and 'Save & Close' — both labels were visible simultaneously.
4. **[Major]** Color-coding alone was used to indicate status — problematic for color-blind users.
5. **[Major]** Participants expected a drag-and-drop interaction where only click-to-select was available.

## Recommendations

1. Conduct a follow-up A/B test comparing the current flow with a simplified alternative.
2. Provide clearer loading and progress indicators for operations exceeding 2 seconds.
3. Increase color contrast ratios to meet WCAG AA standards across all interactive elements.

---
*Report generated from usability testing session on 2026-02-19.*
*6 participants, 6 tasks evaluated.*