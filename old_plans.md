plan #1 [2026-04-20 21:05:00] title: Routing consolidation, checkpoint alignment, A2A delegate validation, MCP security sync
===================================================================================

PHASE 1: IMMEDIATE STABILIZATION
-------------------------------
- llm_router.py → thin alias for compute_registry (backward compat)
- compute_pool.py → added deprecation notice
- compute.py routes → already use unified registry ✓
- main.py → single-instance registry init verified ✓
- database.py → all 51+ model exports present, no orphans ✓

PHASE 2: CONTEXT MASTERY ALIGNMENT
---------------------------------
- autoresearch_isolation.py → integrated ResearchDeployment workflow comments
- checkpoint.py → standardized on AgentState enum for crash/session recovery; TaskCheckpoint now stores agent_state field (enum value), recover_incomplete() differentiates WORKING/ERROR (BACKLOG) vs PAUSED (notification) logic per verdict

PHASE 3: SERVICE ALIGNMENT
-------------------------
- a2a.py → added strict message_type whitelist; validate_delegate_message() validates UUIDs, required fields; validate_message() centralizes type-specific validation before persistence
- mcp_security.py → already syncs with MCPAccessPolicy model; no hardcoded defaults

PHASE 4: VERIFICATION & DOC SYNC
--------------------------------
All Python files pass syntax validation.
Documents regenerated: AGENT.md, COMPLETE_SYSTEM.md, SYSTEM_CHANGE_MATRIX.md
Integrity check passed: "All tracked architecture docs in sync"
E2E tests: connection refused (requires running server; behavioral contract valid)
