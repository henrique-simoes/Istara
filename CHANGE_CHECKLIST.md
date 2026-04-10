# Istara Change Checklist

Use this checklist for EVERY change to ensure nothing breaks. Cross-reference with **SYSTEM_INTEGRITY_GUIDE.md** for details.

`Compass` is the name of the full agentic development system behind this checklist: prompts, generated docs, matrices, technical narrative, personas, and test/simulation maintenance. Updating Compass means updating this whole system so future agents inherit the new truth.

---

## PRE-CHANGE AUDIT

Before making ANY change:

- [ ] Read `SYSTEM_PROMPT.md` for the repo-wide agent contract
- [ ] Read `AGENT_ENTRYPOINT.md` for the canonical reading order
- [ ] Skim `AGENT.md` or `COMPLETE_SYSTEM.md` for the current generated system map
- [ ] Read `SYSTEM_CHANGE_MATRIX.md` for dependent surfaces that must move with this change
- [ ] Decide which parts of Compass must change so the next agent understands the new reality
- [ ] Decide whether `Tech.md` must change because the architecture/process/release story changed
- [ ] Decide whether Istara's own agents need persona updates to understand this feature
- [ ] Decide whether an existing simulation scenario is enough or whether a new scenario must be added
- [ ] Read relevant sections in SYSTEM_INTEGRITY_GUIDE.md
- [ ] Identify all affected subsystems (Database, Routes, Frontend, Agents, Skills, WebSocket)
- [ ] Check if this change involves cascade deletes
- [ ] Verify authentication/authorization impact
- [ ] Plan database migration strategy (if needed)

---

## COMMON CHANGES

### Adding a New Database Model

- [ ] Create `backend/app/models/{entity}.py`
- [ ] Import in `backend/app/models/database.py::init_db()`
- [ ] Implement `to_dict()` method
- [ ] Add proper FK relationships and cascade settings
- [ ] Create `backend/app/services/{entity}_service.py`
- [ ] Create `backend/app/api/routes/{entity}.py` with CRUD endpoints
- [ ] Register router in `backend/app/main.py`
- [ ] Add TypeScript interface to `frontend/src/lib/types.ts`
- [ ] Add API client namespace to `frontend/src/lib/api.ts`
- [ ] Create Zustand store if needed (`frontend/src/stores/{entity}Store.ts`)
- [ ] Add WebSocket event handler if real-time updates needed
- [ ] Write unit tests
- [ ] Update this CHANGE_CHECKLIST.md
- [ ] Run `python scripts/update_agent_md.py`

### Adding a New API Route

- [ ] Create/modify `backend/app/api/routes/{domain}.py`
- [ ] Define request/response Pydantic models
- [ ] Implement endpoint with proper error handling
- [ ] Route automatically protected by SecurityAuthMiddleware (no extra auth code)
- [ ] Register router in `backend/app/main.py`
- [ ] Add corresponding API client method in `frontend/src/lib/api.ts`
- [ ] Add TypeScript types for request/response in `frontend/src/lib/types.ts`
- [ ] Update frontend component(s) to call new endpoint
- [ ] Add WebSocket broadcast if endpoint triggers state changes
- [ ] Test authentication (should return 401 without token)
- [ ] Test with and without required role (if admin-only)
- [ ] Write unit + integration tests
- [ ] Document in API comments

### Adding a New Skill Definition

- [ ] Create `backend/app/skills/definitions/{skill_name}.json` with:
  - name, display_name, description
  - phase (discover/define/develop/deliver)
  - skill_type (analysis/generation/retrieval/validation/transformation)
  - plan_prompt, execute_prompt, output_schema
- [ ] Load at startup via `load_default_skills()` (auto-loaded)
  - OR manually via `POST /api/skills/register?name={skill_name}`
- [ ] Skill auto-registers with no code changes
- [ ] Test skill execution: `POST /api/skills/{name}/execute`
- [ ] Verify findings created with correct structure
- [ ] Check if skill should appear in specialized report sections (update `report_manager.py` SCOPE_MAP if yes)
- [ ] Add to skill recommendation logic if domain-specific
- [ ] Write E2E test covering full execution flow

### Adding a New WebSocket Event Type

- [ ] Add broadcast function to `backend/app/api/websocket.py`:
  ```python
  async def broadcast_my_event(param1: str, ...) -> None:
      await manager.broadcast("my_event_type", {...})
  ```
- [ ] Call broadcast from triggering service/agent:
  ```python
  from app.api.websocket import broadcast_my_event
  await broadcast_my_event(...)
  ```
- [ ] Add event handler in frontend (wherever WebSocket is used):
  ```typescript
  case "my_event_type":
    handleMyEvent(data);
    break;
  ```
- [ ] Update WebSocket docstring to list new event type
- [ ] Verify notification persists to `Notification` table (automatic)
- [ ] Test WebSocket connection with new event type
- [ ] Write E2E test covering broadcast → frontend update

### Adding a New Agent

- [ ] Create `backend/app/agents/{agent_name}.py`
- [ ] Define agent class inheriting from base Agent
- [ ] Implement `async def start()`, `async def stop()`
- [ ] Define capabilities and specialties
- [ ] Import and start in `backend/app/main.py::lifespan()`
- [ ] Test agent startup and heartbeat
- [ ] Verify skill execution
- [ ] Check A2A messaging if needed
- [ ] Update agent documentation
- [ ] Write unit tests for agent logic

### Adding a Messaging Channel

- [ ] Create adapter in `backend/app/channels/{platform}_adapter.py`
- [ ] Implement connection, message receiving, message sending
- [ ] Create database records (ChannelInstance, ChannelMessage, ChannelConversation)
- [ ] Add to channel_router in startup
- [ ] Test message reception → database storage
- [ ] Test finding posting → channel message
- [ ] Verify WebSocket broadcasts `channel_status` and `channel_message`
- [ ] Add credentials storage (encrypted in database)
- [ ] Write integration tests

### Adding a New Computing Node (LLM Server)

- [ ] Register node in ComputeRegistry:
  ```python
  compute_registry.register_node(ComputeNode(...))
  ```
- [ ] Node auto-discovered OR manually registered via `POST /api/compute/nodes`
- [ ] Health check runs immediately
- [ ] Models populate in `ComputeNode.loaded_models`
- [ ] Routing auto-uses new node (no code changes)
- [ ] Monitor `ModelSkillStats` for performance
- [ ] Test skill execution on new node
- [ ] Verify fallback/retry logic works if node goes down

### Modifying a Model Schema

- [ ] **Check cascade impact** — What gets deleted if this model deleted?
- [ ] **Check FK references** — What other models reference this?
- [ ] **For production**: Generate Alembic migration
- [ ] **For dev**: Clear database, re-run `init_db()`
- [ ] Update `to_dict()` method if serialization changes
- [ ] Update TypeScript type in `frontend/src/lib/types.ts`
- [ ] Update API routes that return this model
- [ ] Update frontend components consuming this data
- [ ] Test data integrity: `POST /api/settings/data-integrity`
- [ ] Test orphaned record cleanup
- [ ] Run full test suite

### Changing Authentication/Security

- [ ] Identify all routes affected
- [ ] Test 401/403 responses
- [ ] Verify JWT validation still works (Bearer tokens AND session cookies)
- [ ] Verify HttpOnly cookie auth works (istara_session cookie)
- [ ] Test network security token if enabled
- [ ] Check WebSocket authentication
- [ ] Verify webhook signature validation
- [ ] Test encrypted field access (ENC: prefix fields)
- [ ] Test TOTP 2FA flow (if enabled)
- [ ] Test recovery code generation and verification
- [ ] Test password breach checking (Have I Been Pwned k-anonymity)
- [ ] Verify password hash auto-upgrade on login (PBKDF2 → Argon2id)
- [ ] Test WebAuthn/passkey registration and authentication
- [ ] Run security audit
- [ ] Check Docker container security (cap_drop, read_only, no-new-privileges)
- [ ] Verify TLS/HTTPS configuration (Caddy TLS hardening, HSTS, CSP)
- [ ] Verify security headers (X-Frame-Options, CSP, X-Content-Type-Options)
- [ ] Verify network segmentation (Docker networks: frontend-net, backend-net, data-net)

### Adding Mid-Execution Steering (Agent Communication)

- [ ] Steering queue uses asyncio.Lock for thread safety
- [ ] Steering messages never interrupt in-progress skills (deferred execution)
- [ ] Follow-up messages only processed when agent would otherwise stop
- [ ] Abort clears both queues and signals agent to stop
- [ ] WebSocket events: `steering_message`, `agent_idle` broadcast correctly
- [ ] SteeringInput component shows only when agent is working
- [ ] Queue count badge updates via polling
- [ ] Abort button clears queues and stops current work
- [ ] API routes validate agent existence before queuing
- [ ] SSE `/api/steering/{agent_id}/idle` endpoint handles timeout correctly

### Adding an Integration (Survey, Design, etc.)

- [ ] Create adapter/service file
- [ ] Add database model (SurveyIntegration, etc.)
- [ ] Create routes for setup + sync
- [ ] Implement credential encryption
- [ ] Add webhook receiver if platform uses webhooks
- [ ] Verify data import → finding creation
- [ ] Test error handling (bad credentials, rate limits, etc.)
- [ ] Add to integrations view in frontend
- [ ] Write end-to-end test

---

## DEPLOYMENT CHECKLIST

Before pushing to production:

### Testing
- [ ] All tests pass: `pytest tests/`
- [ ] All E2E tests pass: `pytest tests/e2e_test.py`
- [ ] Simulation scenarios pass: `node tests/simulation/run.mjs`
- [ ] Relevant future-facing test coverage was added or updated for the changed behavior
- [ ] If the changed behavior introduces a new user journey, installer path, onboarding path, release path, or major feature flow, a new simulation scenario was added instead of only stretching unrelated coverage
- [ ] No console errors in browser
- [ ] No error logs in server

### Database
- [ ] Data integrity check passes: `POST /api/settings/data-integrity`
- [ ] No orphaned records found
- [ ] Indexes healthy
- [ ] Vector store dimensions match embedding model
- [ ] Backup exists and is restorable

### Backend
- [ ] All routes accessible with valid JWT
- [ ] Unauthenticated requests rejected (401)
- [ ] Rate limiting working
- [ ] WebSocket connects and receives events
- [ ] All skills execute without errors
- [ ] All agents healthy and responsive
- [ ] ComputeRegistry routes to all nodes

### Frontend
- [ ] No TypeScript errors
- [ ] All components render
- [ ] API calls successful with auth header
- [ ] WebSocket events received and handled
- [ ] Responsive design verified (mobile, tablet, desktop)
- [ ] Accessibility audit passes

### Security
- [ ] JWT secret strong (auto-generated)
- [ ] Encryption key exists and backed up
- [ ] Network token set if not localhost-only
- [ ] No sensitive data in logs
- [ ] Webhook signature validation working
- [ ] Field encryption working for sensitive fields (API keys, tokens)
- [ ] Password hashing uses Argon2id (check `pip show argon2-cffi`)
- [ ] Password breach checking enabled (Have I Been Pwned API accessible)
- [ ] TOTP 2FA available (check `pip show pyotp`)
- [ ] Recovery codes generated for all users
- [ ] HttpOnly session cookies configured (Secure flag requires HTTPS)
- [ ] TLS 1.2+ enforced (Caddy TLS config)
- [ ] HSTS header present in responses
- [ ] CSP header restricts script sources
- [ ] Docker containers hardened (cap_drop, read_only, no-new-privileges)
- [ ] Docker network segmentation active (internal networks for data/backend)
- [ ] Database ports not exposed to host (PostgreSQL, Ollama)

### Documentation
- [ ] Regenerate architecture docs: `python scripts/update_agent_md.py`
- [ ] Integrity check passes: `python scripts/check_integrity.py`
- [ ] Compass was updated anywhere future agents would otherwise be misled
- [ ] `Tech.md` updated if architecture, workflows, or release/update behavior changed
- [ ] Relevant persona files updated if Istara's own agents need to know about the change
- [ ] SYSTEM_INTEGRITY_GUIDE.md updated
- [ ] CHANGE_CHECKLIST.md updated
- [ ] Code comments added for complex logic
- [ ] API docs generated (if using FastAPI docs)
- [ ] README updated with new features

### Configuration
- [ ] .env file configured correctly
- [ ] No hardcoded secrets in code
- [ ] All env vars documented
- [ ] Docker image builds successfully (if using)
- [ ] Docker compose works (if using)

### Release Flow
- [ ] Only release-worthy pushes to `main` are being treated as releases
- [ ] Release preparation run via `./scripts/prepare-release.sh --bump` or `./scripts/prepare-release.sh <version>`
- [ ] Release commit and tag planned together
- [ ] Qualifying `main` pushes, tag pushes, and manual dispatch all match the documented publishing model

### Monitoring
- [ ] Health check endpoint works
- [ ] Heartbeat system responsive
- [ ] Log rotation configured
- [ ] Backup scheduler running
- [ ] Resource monitoring working

---

## ROLLBACK PROCEDURE

If something breaks in production:

1. **Immediate**:
   - [ ] Stop application
   - [ ] Restore database from backup: `POST /api/backups/{id}/restore`
   - [ ] Revert code: `git revert <commit>`
   - [ ] Restart application

2. **Investigation**:
   - [ ] Check error logs
   - [ ] Run data integrity check
   - [ ] Check WebSocket connection status
   - [ ] Verify agent heartbeats

3. **Identify Root Cause**:
   - [ ] Was schema changed? (check migrations)
   - [ ] Was route removed? (check routes still registered)
   - [ ] Was env var renamed? (check config)
   - [ ] Was model deleted? (check cascade impacts)

4. **Fix & Retry**:
   - [ ] Create PR with fix
   - [ ] Run full test suite
   - [ ] Deploy with full deployment checklist
   - [ ] Monitor for 1 hour
   - [ ] Document incident

---

## QUARTERLY REVIEWS

### Code Quality
- [ ] Run linter: `black backend/` `isort backend/`
- [ ] Run type checker: `mypy backend/`
- [ ] Review test coverage
- [ ] Identify dead code
- [ ] Refactor technical debt

### Performance
- [ ] Profile agent execution times
- [ ] Check skill latencies
- [ ] Monitor LLM request/response times
- [ ] Analyze database query performance
- [ ] Review vector search latency

### Security
- [ ] Review access logs for unusual patterns
- [ ] Update dependencies for security patches
- [ ] Rotate encryption key (if policy requires)
- [ ] Audit user roles and permissions
- [ ] Review webhook secret management

### Data Health
- [ ] Run orphaned record cleanup
- [ ] Validate referential integrity
- [ ] Check backup restoration success
- [ ] Review document chunk counts vs files
- [ ] Verify vector store consistency

### Feature Completeness
- [ ] All 53 skills functional
- [ ] All agents healthy
- [ ] All integrations working
- [ ] All routes tested
- [ ] Frontend responsive on all devices

---

## COMMON PITFALLS & HOW TO AVOID THEM

### Pitfall 1: Forgot to Update Types
**Symptom**: Frontend crashes with "property X does not exist on type Y"
**Prevention**:
- [ ] After changing `to_dict()` in model, update TypeScript type
- [ ] Compare field names exactly (case-sensitive)
- [ ] Test API response with frontend

### Pitfall 2: Cascade Delete Orphans Data
**Symptom**: Deleting project deletes unrelated data
**Prevention**:
- [ ] Check all FK relationships in model
- [ ] Set `cascade="all, delete-orphan"` only for true children
- [ ] Set `cascade=None` for references

### Pitfall 3: Route Not Accessible
**Symptom**: 404 or 403 on new endpoint
**Prevention**:
- [ ] Register router in main.py
- [ ] Check route path matches frontend API call
- [ ] Verify JWT is being sent by frontend

### Pitfall 4: WebSocket Event Never Received
**Symptom**: Frontend doesn't update when event broadcast
**Prevention**:
- [ ] Add case handler in WebSocket listener
- [ ] Verify broadcast is called (check logs)
- [ ] Ensure client is connected before broadcast
- [ ] Check event_type matches exactly

### Pitfall 5: Skill Never Executes
**Symptom**: Task stuck in "in_progress", no findings created
**Prevention**:
- [ ] Verify skill registered: `GET /api/skills`
- [ ] Check plan_prompt generates valid plan
- [ ] Check execute_prompt returns valid JSON matching output_schema
- [ ] Check LLM model available on compute node
- [ ] Check task input_document_ids are valid

### Pitfall 6: Performance Degradation
**Symptom**: Responses slow, skills take hours to run
**Prevention**:
- [ ] Monitor ComputeRegistry node health
- [ ] Check LLM server not overloaded
- [ ] Review database indexes
- [ ] Check RAG not retrieving too many chunks
- [ ] Monitor model inference time

### Pitfall 7: Lost Authentication After Revert
**Symptom**: Can't login after rolling back code
**Prevention**:
- [ ] Don't change User schema without migration
- [ ] Keep JWT secret consistent
- [ ] Don't change password hashing algorithm
- [ ] Backup .env file before any change

### Pitfall 8: Data Integrity Check Fails
**Symptom**: `POST /api/settings/data-integrity` reports orphans
**Prevention**:
- [ ] Run check after schema changes
- [ ] Fix orphans: `DELETE FROM table WHERE pk NOT IN (SELECT fk FROM parent)`
- [ ] Restore from backup if unsure
- [ ] Preventive: use cascade deletes properly

---

## USEFUL COMMANDS

### Development
```bash
# Backend
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd frontend
npm run dev  # Starts on http://localhost:3000

# LM Studio
lms server start  # Starts on http://localhost:1234

# Tests
pytest tests/
pytest tests/simulation/run.mjs
python scripts/update_agent_md.py
```

### Production Deployment
```bash
# Docker
docker-compose up -d

# Health check
curl http://localhost:8000/api/health

# Backup
curl -X POST http://localhost:8000/api/backups

# Data integrity
curl http://localhost:8000/api/settings/data-integrity
```

### Debugging
```bash
# Check logs (if using logging)
tail -f /var/log/istara/app.log

# Check database
sqlite3 ./data/istara.db "SELECT COUNT(*) FROM projects;"

# Check LLM model loaded
curl http://localhost:1234/v1/models

# Check compute nodes
curl http://localhost:8000/api/compute/nodes \
  -H "Authorization: Bearer $TOKEN"
```

---

## REFERENCES

- **Full System Guide**: `SYSTEM_INTEGRITY_GUIDE.md`
- **Architecture**: `Tech.md`
- **Development Patterns**: `CLAUDE.md`
- **Agent Capabilities**: `AGENT.md` (auto-generated)

---

**Last Updated**: 2026-03-28
**Maintainer**: Development Team
**Version**: 0.1.0
