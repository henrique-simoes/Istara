# Usability Test Report — Search and Navigation Overhaul

**Date:** 2026-01-23
**Product:** Project management platform (TechStart Inc)
**Research Goal:** Reduce support tickets related to 'can't find feature' by 35%
**Participants:** 4 (Product Designer, Sales Lead, Marketing Manager, Frontend Developer)
**Methodology:** Moderated remote usability testing with think-aloud protocol

## Participants

| ID | Name | Role | Company Size | Age |
|----|------|------|-------------|-----|
| P20 | Jessica Nguyen | Product Designer | 50-200 | 29 |
| P04 | James O'Brien | Sales Lead | 200-500 | 38 |
| P10 | Rachel Kim | Marketing Manager | 10-50 | 31 |
| P12 | Sofia Rossi | Frontend Developer | 50-200 | 27 |

## Tasks

### Task 1: Use the breadcrumb trail to return to a previous page

- **Completion rate:** 40%
- **Average time:** 167s
- **Errors observed:** 0
- **Participant observations:**
  - James O'Brien (Sales Lead): "The integration with our CI/CD pipeline means developers never have to leave the tool to update task status"
  - Sofia Rossi (Frontend Developer): "I can't set different notification preferences for different projects"
  - Rachel Kim (Marketing Manager): "The tool doesn't warn me before I navigate away from an unsaved form"
  - Jessica Nguyen (Product Designer): "The dark mode has contrast issues that make some status badges completely invisible"

### Task 2: Navigate to a deeply nested settings page

- **Completion rate:** 97%
- **Average time:** 87s
- **Errors observed:** 1
- **Participant observations:**
  - James O'Brien (Sales Lead): "There's no keyboard shortcut for the one action I do fifty times a day"
  - Jessica Nguyen (Product Designer): "I can't tell which items in my inbox need my action versus which are just informational"
  - Rachel Kim (Marketing Manager): "I can't tell which items in my inbox need my action versus which are just informational"

### Task 3: Search for a team member by name

- **Completion rate:** 81%
- **Average time:** 164s
- **Errors observed:** 0
- **Participant observations:**
  - James O'Brien (Sales Lead): "I can't tell which items in my inbox need my action versus which are just informational"
  - Sofia Rossi (Frontend Developer): "It took me way too long to figure out how to invite my team"

### Task 4: Find a specific project using the search bar

- **Completion rate:** 68%
- **Average time:** 140s
- **Errors observed:** 3
- **Participant observations:**
  - Jessica Nguyen (Product Designer): "There's a bug where if you scroll too fast the page goes blank and you have to reload"
  - James O'Brien (Sales Lead): "My manager asked me to pull a report and it took me forty-five minutes to figure out how"
  - Rachel Kim (Marketing Manager): "The loading time is really frustrating, especially when I'm trying to pull up something in a meeting"

### Task 5: Locate the help documentation for a feature

- **Completion rate:** 80%
- **Average time:** 63s
- **Errors observed:** 1
- **Participant observations:**
  - Rachel Kim (Marketing Manager): "My team actually enjoys doing status updates now because the interface makes it quick and painless"
  - James O'Brien (Sales Lead): "The tooltips appear too slowly and disappear too quickly to actually read them"

### Task 6: Find a recently accessed item without using search

- **Completion rate:** 92%
- **Average time:** 136s
- **Errors observed:** 0
- **Participant observations:**
  - Jessica Nguyen (Product Designer): "The contrast between read and unread items is so subtle I can't tell them apart"
  - James O'Brien (Sales Lead): "I think the mobile notifications could be smarter, right now I get alerts for things that don't need my attention"
  - Sofia Rossi (Frontend Developer): "I created a template but there's no way to share it with the rest of my organization"

## SUS Score

**Overall SUS Score: 59 / 100** — Grade: C — OK (below average for usability)

The system scores below the industry average (68), indicating significant usability concerns that should be addressed before the next release.

## Key Findings

1. **[Major]** The loading state provided no progress indication, leading two participants to refresh the page.
2. **[Major]** Users consistently hesitated before clicking the primary CTA — the label was ambiguous.
3. **[Minor]** Inconsistent button placement across different sections confused navigation patterns.
4. **[Minor]** The empty state provided no guidance on how to get started.
5. **[Minor]** The breadcrumb trail did not update after a multi-step action, leaving users disoriented.
6. **[Cosmetic]** Font size in the data table was too small for comfortable reading during extended use.

## Recommendations

1. Add visible text labels alongside icon-only buttons in the toolbar.
2. Increase color contrast ratios to meet WCAG AA standards across all interactive elements.
3. Improve empty states with actionable guidance to reduce user confusion on first use.
4. Provide clearer loading and progress indicators for operations exceeding 2 seconds.
5. Review and consolidate notification preferences into a single, well-organized settings page.

---
*Report generated from usability testing session on 2026-01-23.*
*4 participants, 6 tasks evaluated.*