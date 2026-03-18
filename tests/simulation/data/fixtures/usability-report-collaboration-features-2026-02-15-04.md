# Usability Test Report — Collaboration Features

**Date:** 2026-02-15
**Product:** Collaborative learning management system (EduVerse)
**Research Goal:** Increase team workspace adoption from 23% to 50% of active accounts
**Participants:** 8 (Support Specialist, Product Manager, Product Owner, Engineering Manager, VP of Product, Content Strategist, Customer Success Lead, DevOps Lead)
**Methodology:** Moderated remote usability testing with think-aloud protocol

## Participants

| ID | Name | Role | Company Size | Age |
|----|------|------|-------------|-----|
| P17 | Liam Murphy | Support Specialist | 50-200 | 25 |
| P01 | Sarah Chen | Product Manager | 50-200 | 32 |
| P30 | Omar Hassan | Product Owner | 200-500 | 35 |
| P21 | Raj Krishnamurthy | Engineering Manager | 200-500 | 42 |
| P11 | David Okonkwo | VP of Product | 500-2000 | 48 |
| P22 | Hannah Eriksson | Content Strategist | 10-50 | 35 |
| P07 | Emily Watson | Customer Success Lead | 200-500 | 34 |
| P25 | Pavel Volkov | DevOps Lead | 200-500 | 40 |

## Tasks

### Task 1: Assign a task to another team member

- **Completion rate:** 80%
- **Average time:** 121s
- **Errors observed:** 1
- **Participant observations:**
  - Liam Murphy (Support Specialist): "The workload balancing view finally made it obvious when someone was overloaded"
  - Hannah Eriksson (Content Strategist): "I tried to set up the integration with Slack three times and it failed silently each time"

### Task 2: Share a document with a specific team member

- **Completion rate:** 61%
- **Average time:** 53s
- **Errors observed:** 0
- **Participant observations:**
  - Sarah Chen (Product Manager): "The placeholder text in the search box vanishes too quickly before I can read what formats are supported"
  - Hannah Eriksson (Content Strategist): "The tool shows me information I don't have permission to act on, which is confusing"
  - Liam Murphy (Support Specialist): "The automations feature was a bit overwhelming at first but once I set up a few rules it saved hours every week"
  - Emily Watson (Customer Success Lead): "I appreciate that keyboard navigation works everywhere, I rarely need to touch my mouse"

### Task 3: Set permissions on a shared folder

- **Completion rate:** 50%
- **Average time:** 174s
- **Errors observed:** 1
- **Participant observations:**
  - Omar Hassan (Product Owner): "The batch operations saved me so much time during our annual project cleanup"
  - Sarah Chen (Product Manager): "I would absolutely recommend it to my team, with a few caveats"
  - Emily Watson (Customer Success Lead): "I think the mobile notifications could be smarter, right now I get alerts for things that don't need my attention"
  - Pavel Volkov (DevOps Lead): "I wish more tools had this level of thought put into the empty states, it's clear what you need to do"

### Task 4: Create a shared workspace and invite collaborators

- **Completion rate:** 63%
- **Average time:** 108s
- **Errors observed:** 3
- **Participant observations:**
  - Liam Murphy (Support Specialist): "The chart visualization is misleading because the Y-axis doesn't start at zero and you can't change it"
  - Emily Watson (Customer Success Lead): "The tool doesn't warn me before I navigate away from an unsaved form"
  - Hannah Eriksson (Content Strategist): "The print view is unusable, it cuts off text and doesn't paginate properly"

### Task 5: Track changes made by collaborators

- **Completion rate:** 54%
- **Average time:** 102s
- **Errors observed:** 3
- **Participant observations:**
  - Liam Murphy (Support Specialist): "The commenting system on tasks is way better than email chains, nothing gets lost"
  - Emily Watson (Customer Success Lead): "It feels like it was designed by engineers for engineers, not for someone like me"
  - Omar Hassan (Product Owner): "I can't tell which items in my inbox need my action versus which are just informational"
  - Pavel Volkov (DevOps Lead): "The link previews don't work for internal pages, so shared links are just cryptic URLs"

### Task 6: View and resolve a comment thread

- **Completion rate:** 99%
- **Average time:** 40s
- **Errors observed:** 0
- **Participant observations:**
  - Hannah Eriksson (Content Strategist): "The integration with our CI/CD pipeline means developers never have to leave the tool to update task status"
  - Omar Hassan (Product Owner): "What frustrates me is that the free tier is so limited you can't really evaluate the product properly"
  - Pavel Volkov (DevOps Lead): "I've used probably a dozen project management tools and this one has the best learning curve"
  - Sarah Chen (Product Manager): "I was pleasantly surprised by how fast the search results came back"

## SUS Score

**Overall SUS Score: 65 / 100** — Grade: C — OK (below average for usability)

The system scores below the industry average (68), indicating significant usability concerns that should be addressed before the next release.

## Key Findings

1. **[Critical]** 3 out of 5 participants attempted to use the back button instead of the in-app navigation, causing loss of form state.
2. **[Critical]** Participants missed critical information below the fold — no visual cue indicated more content.
3. **[Critical]** Icon-only buttons lacked labels, and 4 of 5 participants could not identify their function.
4. **[Major]** Spacing between interactive elements was too tight, causing frequent mis-taps on mobile.
5. **[Minor]** The modal dialog could not be dismissed with the Escape key, violating accessibility expectations.
6. **[Minor]** The empty state provided no guidance on how to get started.
7. **[Cosmetic]** Font size in the data table was too small for comfortable reading during extended use.

## Recommendations

1. Improve empty states with actionable guidance to reduce user confusion on first use.
2. Add a persistent breadcrumb trail that updates in real time during multi-step flows.
3. Add keyboard shortcut support for the 10 most common user actions.
4. Provide clearer loading and progress indicators for operations exceeding 2 seconds.

---
*Report generated from usability testing session on 2026-02-15.*
*8 participants, 6 tasks evaluated.*