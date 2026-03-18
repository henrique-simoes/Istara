# Usability Test Report — Pricing Page Conversion

**Date:** 2026-03-03
**Product:** Patient portal and telehealth platform (HealthBridge)
**Research Goal:** Increase free-to-paid conversion rate from 3.1% to 5%
**Participants:** 6 (Engineering Manager, Business Analyst, Support Specialist, Data Analyst, Engineering Director, DevOps Lead)
**Methodology:** Moderated remote usability testing with think-aloud protocol

## Participants

| ID | Name | Role | Company Size | Age |
|----|------|------|-------------|-----|
| P21 | Raj Krishnamurthy | Engineering Manager | 200-500 | 42 |
| P27 | Kwame Asante | Business Analyst | 2000+ | 31 |
| P17 | Liam Murphy | Support Specialist | 50-200 | 25 |
| P08 | Wei Zhang | Data Analyst | 50-200 | 29 |
| P02 | Marcus Johnson | Engineering Director | 500-2000 | 45 |
| P25 | Pavel Volkov | DevOps Lead | 200-500 | 40 |

## Tasks

### Task 1: Find cancellation or downgrade options

- **Completion rate:** 72%
- **Average time:** 127s
- **Errors observed:** 2
- **Participant observations:**
  - Liam Murphy (Support Specialist): "Our team velocity actually improved twenty percent in the first quarter after adopting it"
  - Kwame Asante (Business Analyst): "There's no way to see a chronological history of changes to a single task"
  - Pavel Volkov (DevOps Lead): "The way archived projects are handled is clean, they're out of the way but easy to find when you need them"
  - Raj Krishnamurthy (Engineering Manager): "I can't drag tasks between different project boards, so I end up duplicating them manually"

### Task 2: Compare features across pricing tiers

- **Completion rate:** 42%
- **Average time:** 32s
- **Errors observed:** 1
- **Participant observations:**
  - Raj Krishnamurthy (Engineering Manager): "The tag system is incredibly flexible, we use it for priority, department, client, and sprint all at once"
  - Kwame Asante (Business Analyst): "The placeholder text in the search box vanishes too quickly before I can read what formats are supported"
  - Marcus Johnson (Engineering Director): "The way it handles dependencies between tasks is really elegant, I haven't seen that done better anywhere"
  - Liam Murphy (Support Specialist): "Every time I export a report, the formatting is completely off and I have to fix it in Excel"

### Task 3: Identify which plan includes the feature you need

- **Completion rate:** 50%
- **Average time:** 60s
- **Errors observed:** 3
- **Participant observations:**
  - Kwame Asante (Business Analyst): "Every time there's an update, my custom workflow automations break and I have to rebuild them"
  - Liam Murphy (Support Specialist): "I was confused by the terminology, what you call a workspace I would call a project"
  - Wei Zhang (Data Analyst): "The calendar integration was the tipping point for us, we were already using it but that made it indispensable"

### Task 4: Calculate the cost for your team size

- **Completion rate:** 42%
- **Average time:** 15s
- **Errors observed:** 1
- **Participant observations:**
  - Wei Zhang (Data Analyst): "The permission system is surprisingly granular, we can control exactly who sees what"
  - Pavel Volkov (DevOps Lead): "The mobile app is fine for checking things, but I'd never try to do real work on it"
  - Liam Murphy (Support Specialist): "It feels like it was designed by engineers for engineers, not for someone like me"
  - Marcus Johnson (Engineering Director): "I had to watch a YouTube tutorial to understand the reporting feature, and that shouldn't be necessary"

### Task 5: Locate the enterprise contact form

- **Completion rate:** 40%
- **Average time:** 64s
- **Errors observed:** 3
- **Participant observations:**
  - Marcus Johnson (Engineering Director): "The commenting system on tasks is way better than email chains, nothing gets lost"
  - Liam Murphy (Support Specialist): "I keep getting logged out randomly in the middle of my work"

### Task 6: Find the monthly vs. annual pricing toggle

- **Completion rate:** 69%
- **Average time:** 26s
- **Errors observed:** 0
- **Participant observations:**
  - Liam Murphy (Support Specialist): "The table sort only works on one column at a time and doesn't remember my preference"
  - Raj Krishnamurthy (Engineering Manager): "My manager asked me to pull a report and it took me forty-five minutes to figure out how"

## SUS Score

**Overall SUS Score: 45 / 100** — Grade: D — Poor

The system scores below the industry average (68), indicating significant usability concerns that should be addressed before the next release.

## Key Findings

1. **[Critical]** 3 out of 5 participants attempted to use the back button instead of the in-app navigation, causing loss of form state.
2. **[Major]** Users consistently hesitated before clicking the primary CTA — the label was ambiguous.
3. **[Major]** Auto-complete suggestions in the search bar were irrelevant for the top 3 most common queries.
4. **[Major]** Form validation only triggered on submit, not inline, causing repeated correction cycles.
5. **[Minor]** The breadcrumb trail did not update after a multi-step action, leaving users disoriented.
6. **[Minor]** The success confirmation message disappeared too quickly for most participants to read.

## Recommendations

1. Increase color contrast ratios to meet WCAG AA standards across all interactive elements.
2. Add visible text labels alongside icon-only buttons in the toolbar.
3. Improve empty states with actionable guidance to reduce user confusion on first use.
4. Add inline validation to multi-step forms to reduce error-correction cycles.

---
*Report generated from usability testing session on 2026-03-03.*
*6 participants, 6 tasks evaluated.*