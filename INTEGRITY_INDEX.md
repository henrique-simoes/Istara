# ReClaw System Integrity Documentation Index

**Created**: 2026-03-28
**System Version**: v0.1.0 (Post-ComputeRegistry Unification)
**Status**: Complete System Mapping

---

## Quick Navigation

### I'm a Developer Making a Change
→ Start here: **CHANGE_CHECKLIST.md**
- Pre-change audit checklist
- Change-type specific procedures
- Deployment checklist
- Common pitfalls

### I'm Reviewing a Pull Request
→ Use: **CHANGE_CHECKLIST.md** + **SYSTEM_INTEGRITY_GUIDE.md**
1. Identify change type (model, route, skill, etc.)
2. Check CHANGE_CHECKLIST.md for required updates
3. Cross-reference SYSTEM_INTEGRITY_GUIDE.md for details
4. Verify all affected subsystems

### I'm Troubleshooting a Problem
→ Use: **INVESTIGATION_SUMMARY.md** + **SYSTEM_INTEGRITY_GUIDE.md**
1. Check "Common Pitfalls" in CHANGE_CHECKLIST.md
2. Review "Critical Paths" in INVESTIGATION_SUMMARY.md
3. Check relevant section in SYSTEM_INTEGRITY_GUIDE.md
4. Use debugging commands in CHANGE_CHECKLIST.md

### I'm Planning a New Feature
→ Use: **SYSTEM_INTEGRITY_GUIDE.md**
1. Identify affected subsystems
2. Review relevant model/route/agent section
3. Check Change Complexity Matrix in INVESTIGATION_SUMMARY.md
4. Follow CHANGE_CHECKLIST.md for implementation

### I'm Optimizing Performance
→ Use: **INVESTIGATION_SUMMARY.md** (Monitoring Recommendations section)
1. Monitor metrics from recommendation list
2. Check critical paths
3. Profile using commands in CHANGE_CHECKLIST.md
4. Consult SYSTEM_INTEGRITY_GUIDE.md for architecture details

### I'm Onboarding a New Developer
→ Hand them this sequence:
1. INVESTIGATION_SUMMARY.md (20 min read - architecture overview)
2. SYSTEM_INTEGRITY_GUIDE.md sections 1-5 (1 hour read - core concepts)
3. CLAUDE.md (development patterns)
4. CHANGE_CHECKLIST.md (reference guide)

---

## The Three Documents

### 1. SYSTEM_INTEGRITY_GUIDE.md (25,000+ words)
**The Complete Reference Manual**

What's inside:
- Executive summary of architecture principles
- Complete database model registry (51+ models)
- Complete API route registry (35 modules, 200+ endpoints)
- Agent system architecture (6 system agents + custom workers)
- Skill system (53 skills, factory pattern)
- Compute registry (unified LLM orchestration)
- Frontend structure (components, stores, types, API client)
- WebSocket events (16 broadcast types)
- Configuration and security
- Integration points (channels, design tools, surveys, MCP)
- Testing guidance
- 6 critical data flows (end-to-end traces)
- Change impact matrix
- Quarterly maintenance checklists

**Use when you need**: Deep understanding of a subsystem, full system context, data flow details, model relationships, security model

**Time to read**: 2-3 hours (can skim by section)

---

### 2. CHANGE_CHECKLIST.md (5,000+ words)
**The Developer's Handbook**

What's inside:
- Pre-change audit (what to check before modifying)
- Common changes:
  - Adding database model (10 steps)
  - Adding API route (8 steps)
  - Adding skill (5 steps)
  - Adding WebSocket event (5 steps)
  - Adding agent (6 steps)
  - Adding integration (8 steps)
  - Modifying schema (9 steps)
  - Security changes (6 steps)
- Deployment checklist (40 items)
- Rollback procedure
- Quarterly review tasks
- Common pitfalls with preventions
- Useful debugging commands

**Use when you need**: Step-by-step guidance for a specific change, deployment readiness verification, rollback instructions, debugging help

**Time to use**: 10-30 min per change (follow the checklist)

---

### 3. INVESTIGATION_SUMMARY.md (3,000+ words)
**The Executive Overview**

What's inside:
- Investigation scope and methodology
- Key findings (strengths and weaknesses)
- Architecture assessment
- Critical system boundaries
- Change complexity matrix (red/yellow/green)
- Deployment readiness assessment
- Critical paths to protect
- Testing coverage gaps
- Monitoring recommendations
- Future improvements roadmap
- How to use all three documents

**Use when you need**: Quick overview, risk assessment, change complexity estimation, deployment decisions, incident response prioritization

**Time to read**: 30 min

---

## Document Cross-References

### If you're... → Read this section in...

**Adding a database model**
- SYSTEM_INTEGRITY_GUIDE.md → "Database & Model Layer"
- CHANGE_CHECKLIST.md → "Adding a New Database Model"

**Adding an API endpoint**
- SYSTEM_INTEGRITY_GUIDE.md → "API Routes & Endpoints"
- CHANGE_CHECKLIST.md → "Adding a New API Route"

**Adding a skill**
- SYSTEM_INTEGRITY_GUIDE.md → "Skill System"
- CHANGE_CHECKLIST.md → "Adding a New Skill Definition"

**Adding an agent**
- SYSTEM_INTEGRITY_GUIDE.md → "Agent System Architecture"
- CHANGE_CHECKLIST.md → "Adding a New Agent"

**Understanding data flow**
- SYSTEM_INTEGRITY_GUIDE.md → "Critical Data Flows"
- INVESTIGATION_SUMMARY.md → "Critical Paths to Protect"

**Understanding security**
- SYSTEM_INTEGRITY_GUIDE.md → "Configuration & Security"
- INVESTIGATION_SUMMARY.md → "Authentication Boundary"

**Planning a feature**
- INVESTIGATION_SUMMARY.md → "Change Complexity Matrix"
- SYSTEM_INTEGRITY_GUIDE.md → "Cross-Cutting Concerns & Change Impact Matrix"
- CHANGE_CHECKLIST.md → relevant change type

**Troubleshooting**
- CHANGE_CHECKLIST.md → "Common Pitfalls & How to Avoid Them"
- INVESTIGATION_SUMMARY.md → "Critical Paths to Protect"
- SYSTEM_INTEGRITY_GUIDE.md → affected subsystem

**Deploying to production**
- CHANGE_CHECKLIST.md → "Deployment Checklist"
- INVESTIGATION_SUMMARY.md → "Deployment Readiness Assessment"

---

## Key Facts (TL;DR)

**Database**
- 51+ models registered in init_db()
- All data scoped to Project (cascade delete on deletion)
- 5-layer atomic research chain: Nugget → Fact → Insight → Recommendation → CodeApplication
- Double Diamond phases: discover/define/develop/deliver

**API**
- 35 route modules, 200+ endpoints
- ALL endpoints require JWT (except /api/auth/*, /api/health, /webhooks/*)
- SecurityAuthMiddleware enforces auth globally
- Response schemas match TypeScript types exactly

**Agents**
- 6 system agents (TASK_EXECUTOR, DEVOPS_AUDIT, UI_AUDIT, UX_EVALUATION, USER_SIMULATION, CUSTOM)
- Coordinate via A2AMessage table
- Heartbeat every 60s (configurable)
- All agent activity audited

**Skills**
- 53 skills (10 discover, 12 define, 15 develop, 12 deliver, 4 generic)
- JSON-based definitions (no code changes needed)
- Factory pattern creates skill classes at runtime
- Performance tracked per model × skill in ModelSkillStats

**Compute**
- ComputeRegistry is single source of truth for all LLM compute
- Unified registry for local, network, and relay nodes
- Health checking, automatic failover, capability filtering
- Replaces old LLMRouter + ComputePool

**Frontend**
- React with Zustand (14 stores)
- 23 component groups across layout, chat, kanban, findings, documents, skills, agents, etc.
- All types in single types.ts file
- API client uses namespace pattern (api.projects.list(), api.tasks.create(), etc.)

**WebSocket**
- 16 broadcast event types (agent_status, task_progress, finding_created, etc.)
- JWT auth required (?token= query parameter)
- All broadcasts auto-persisted to Notification table
- Real-time updates trigger store updates in frontend

**Security**
- JWT (local or team mode)
- Network access token (optional, for non-localhost)
- Field encryption (sensitive data like API keys)
- Webhook signature validation
- No hardcoded secrets

---

## When to Update These Docs

- **Daily**: As you code, keep code comments in sync with SYSTEM_INTEGRITY_GUIDE.md
- **Per Feature**: After merging a feature, update relevant section if architecture changed
- **Per Release**: Review and update before tagging release
- **Quarterly**: Run through checklists, verify system still accurate

---

## Maintenance Responsibility

Keep these docs current:
- Every time you add/modify/delete a model → update Database section
- Every time you add/modify/delete a route → update API Routes section
- Every time you add/modify a skill → update Skill System section
- Every time you add a WebSocket event → update WebSocket Events section
- Every time you change security → update Configuration & Security section

**Outdated docs are worse than no docs** — they mislead developers.

---

## Questions & Answers

**Q: Which document should I read first?**
A: INVESTIGATION_SUMMARY.md (30 min). It gives you context for the other two.

**Q: Can I just read the checklist and skip the guide?**
A: For simple changes, yes. For complex changes or deep understanding, read the guide too.

**Q: What if the docs contradict the code?**
A: The code is the source of truth. File an issue to update docs. Don't follow outdated docs.

**Q: How do I know if my change is complete?**
A: Go through the CHANGE_CHECKLIST.md for your change type. Check all boxes. If one is blocked, that's your gap.

**Q: What's the most critical thing I should know?**
A: **Every change touches multiple subsystems.** Use the Change Complexity Matrix to identify what you missed. Test thoroughly before merging.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-28 | Initial complete system integrity investigation |

---

**Status**: Active and maintained
**Last Reviewed**: 2026-03-28
**Next Review**: 2026-06-28 (quarterly)

For updates, corrections, or additions → see SYSTEM_INTEGRITY_GUIDE.md or CHANGE_CHECKLIST.md
