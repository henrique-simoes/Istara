# Echo -- User Simulation Agent Skills

## Simulation Capabilities

### User Journey Simulation
- Create realistic research projects with proper names, descriptions, and context
- Upload simulated research documents (interview transcripts, survey responses, competitor reports)
- Execute research skills through the API and verify output quality
- Manage tasks on the Kanban board: create, prioritize, assign, track progress, complete
- Navigate between features simulating real user navigation patterns
- Simulate multi-session workflows: start a task in one session, resume it in another

### Edge Case Testing
- Empty state testing: new projects with no data, empty search results, no messages, zero findings
- Boundary value testing: maximum-length inputs, zero-length inputs, special characters, Unicode, emoji, RTL text
- Concurrent operation testing: multiple actions in rapid succession, parallel API calls, duplicate submissions
- State transition testing: interrupting workflows mid-stream, closing sessions during operations, browser back button
- Large data testing: projects with many files, long conversation histories, extensive findings databases
- Input fuzzing: unexpected data types, SQL injection patterns, XSS payloads (for safety verification, not exploitation)

### Error Recovery Testing
- Trigger known error conditions and verify graceful handling
- Test with invalid inputs, missing parameters, and malformed requests
- Verify error messages are user-friendly and actionable (not raw stack traces)
- Test recovery paths: can the user continue working after an error without losing data?
- Check that errors don't leave the system in an inconsistent state (no half-created records)
- Verify timeout behavior: what happens when LLM inference takes longer than expected?

### Regression Testing
- Maintain a suite of critical path tests that must pass on every run
- Compare results against baseline expectations for known-good behavior
- Detect performance regressions: endpoints that became slower, features that broke
- Verify that fixed bugs remain fixed after subsequent changes
- Track test stability: which tests are flaky, which are reliable, and why

### Integration Testing
- Test the full cycle: project creation -> file upload -> skill execution -> findings review
- Verify cross-feature data flow: chat messages reference correct project context
- Test agent coordination: main agent picks up tasks, DevOps audits detect issues
- Verify WebSocket updates propagate correctly for task progress and agent status
- Test the Atomic Research chain end-to-end: document -> nuggets -> facts -> insights -> recommendations
- Verify that deleting upstream data (a document) properly cascades or flags downstream dependencies

### Performance Assessment
- Track API response times across all endpoints (baseline, p50, p95, p99)
- Identify endpoints that exceed acceptable latency thresholds (> 2s for interactive, > 30s for background)
- Detect memory leaks or growing resource consumption over extended simulation runs
- Monitor database query performance through response time patterns
- Measure skill execution duration and compare against historical baselines

### Scenario Generation
- **Happy path scenarios**: Standard workflows executed correctly. These should always pass.
- **Sad path scenarios**: Common error conditions (file too large, invalid format, network timeout). These should fail gracefully.
- **Evil path scenarios**: Adversarial inputs, race conditions, resource exhaustion. These test defensive robustness.
- **Chaos scenarios**: Random combinations of operations in random order. These find unexpected interactions.

## Reporting
- Generate structured simulation reports with: scenario name, steps, expected/actual behavior, pass/fail, severity
- Calculate overall simulation scores: total checks, pass rate, critical failures, mean response time
- Track simulation history for trend analysis (are we getting better or worse?)
- Provide actionable recommendations for each failure with reproduction steps
- Generate a "platform confidence score" based on test coverage and pass rates

## Test Data Standards
- All test projects: named with "SIM:" prefix (e.g., "SIM: Q4 Usability Study")
- All test files: use realistic but synthetic content, never real participant data
- All test users: use simulation-specific identifiers, never real user IDs
- Cleanup verification: after every run, verify zero SIM-prefixed records remain in the database

## Integration Testing Scenarios
- **Channel lifecycle**: Create instance → start → health check → send message → fetch history → stop → delete. Verify WebSocket events fired at each transition.
- **Multi-instance**: Create two Telegram bots, verify both operate independently, messages route to correct instance
- **Deployment simulation**: Create deployment → link channels → activate → simulate incoming responses → verify adaptive follow-ups → check conversation state transitions → verify findings created
- **Survey webhook ingestion**: Simulate SurveyMonkey/Typeform webhook POST → verify signature validation → verify Nuggets created → verify response count incremented
- **MCP server security**: Verify MCP disabled by default → enable → test default policy denies SENSITIVE tools → enable specific tools → verify access control → verify audit logging → disable
- **MCP client registry**: Register external server → discover tools → cache tools → call tool → health check → unregister
- **Cross-system integration**: Deploy interview via Telegram → responses create Nuggets → Nuggets available in RAG → chat can discuss interview results
- **Error scenarios**: Invalid channel credentials → graceful error. Webhook from unknown source → rejected. MCP request for denied tool → audit logged as denied.

## Autoresearch Experiment Validation
- Validate isolation: run autoresearch loop → verify zero AgentLearning records created during experiment
- Validate persona lock: acquire lock → verify self-evolution promote_learning blocked → release → verify unblocked
- Validate rate limiting: exceed daily experiment limit → verify engine stops gracefully
- Validate model/temp loop: run on a skill → verify model_skill_stats populated with correct data
- Validate skill prompt loop: verify quality score improves, skill version incremented on kept mutations
- Validate mutual exclusion: create meta-hyperagent variant → verify conflicting autoresearch loop skips

## Laws of UX Awareness (Yablonski, 2024)
- Simulate user behavior reflecting psychological laws: Hick's Law (longer decisions with more options), Miller's Law (can't hold >7 items), Peak-End Rule (remembers endings), Paradox of Active User (skips tutorials)
- Test scenarios should validate law compliance: does the UI respect Fitts's Law (adequate target sizes)? Does navigation follow Serial Position Effect (important items first/last)?
- Laws of UX API tests: verify /api/laws returns 30 laws, keyword matching works, compliance scoring aggregates correctly

## UI Feature Simulation Scenarios (v2024-Q4 Update)

### View Persistence Testing
- Simulate navigation to each view, trigger page refresh, verify the same view is restored from localStorage. Test edge cases: corrupted localStorage value, view that was removed/renamed, localStorage quota exceeded. Verify document title updates to match current view name after each navigation.

### Compact Document Views Testing
- Simulate switching between Compact, Grid, and List modes. Verify all documents render correctly in each mode. Test: mode preference persists across sessions, switching modes preserves selection state, Compact mode renders single-line rows even with long document titles (truncation with tooltip), Grid mode shows card layout, List mode shows tall cards.

### Skills Self-Evolution Layout Testing
- Simulate viewing self-improvement proposals alongside creation proposals. Verify two-column layout renders without overlap. Test: creation proposal prompt preview displays full content with scroll, responsive behavior on narrow viewports (columns stack), clicking a proposal opens the correct detail/approval flow.

### Agent Error Surfacing Testing
- Simulate agent heartbeat loss by disconnecting WebSocket. Verify card transitions from healthy to "Heartbeat Lost" status. Verify Recent Errors section populates with actual work log errors. Test: error details match real log entries, heartbeat recovery transitions card back to healthy, rapid connect/disconnect cycles do not leave stale error states.

### Convergence Pyramid Interactivity Testing
- Simulate clicking report cards at each pyramid level. Verify detail panel opens with correct findings, documents, tags, and MECE categories. Test: clicking multiple cards in sequence, closing and reopening panels, detail panel for empty pyramid levels (graceful empty state), keyboard navigation through pyramid cards.

### UX Laws Violation Badges Testing
- Simulate creating findings tagged with UX law IDs. Verify violation count badges update on law cards. Test: "View violations" navigates to correctly filtered findings list, badge count matches actual finding count, removing a finding updates the badge count, laws with zero violations show no badge.

### Task Document Attachments Testing
- Simulate creating tasks and attaching documents. Verify attachment indicators appear on task cards. Test: attach multiple documents, detach a document, verify TaskEditor shows correct attachment list, verify detached documents are no longer linked, edge case of attaching the same document twice.

### Settings Navigation Testing
- Verify Settings appears in primary nav without clicking "More". Simulate navigation to Settings from any view. Test: Settings active state displays correctly, keyboard navigation reaches Settings in the expected tab order, Settings route works after page refresh.

### Integrations ErrorBoundary Testing
- Simulate integration loading failures. Verify ErrorBoundary catches the error and displays a recovery UI (not a blank screen or crash). Test: retry action after error, navigation away and back to Integrations after error, concurrent integration failures.

### Scroll & Overflow Testing
- Simulate large datasets in Compute Pool view, verify full scrollability. Simulate long content in Meta-Agent view, verify no layout overflow. Simulate rapid message arrival in Chat, verify scroll stays anchored to bottom for new messages. Test: manual scroll-up during message arrival preserves position, scroll-to-bottom button appears when scrolled up.

### Compute Pool Streaming & Relay Simulation Scenarios
- **Relay capability detection**: Register a relay node, then verify the health check probes the relay's provider via HTTP and populates capabilities (tool support, context length, vision). Verify capability badges appear in the compute pool API response.
- **Network/Relay deduplication**: Register a network node, then register a relay pointing to the same provider host. Verify the network node is automatically removed and only the relay entry remains. Verify re-registering the relay does not create duplicates.
- **Relay host resolution**: Register a relay that reports `provider_host: "http://localhost:1234"`. Verify the backend resolves localhost to the relay's actual IP. Test streaming a request through the relay — verify the response completes successfully (not a connection-refused error).
- **Tool filter with unknown capabilities**: Register a node before capability detection completes. Verify the node is NOT excluded from tool-support filtered queries — it should be eligible to serve requests. After detection completes, verify filtering works correctly based on actual capabilities.
- **Network discovery skip**: Establish a relay connection, then trigger a network scan. Verify the scan does not re-register a node for the relay-covered provider. After relay disconnects, verify the next scan can re-discover the node as a network entry.
- **No "Local Only" when relay online**: With a relay connected, verify the compute pool does not show misleading "Local Only" status. The pool should reflect that remote compute is available via the relay.

### Feature Update — March 2026 Simulation Scenarios
- **Surveys and MCP API unwrapping**: Call `/api/integrations` and `/api/mcp/servers`, verify responses return wrapped objects (`{integrations: [], servers: []}`), not raw arrays. Parse the wrapper and verify the inner array is correctly typed. Test edge case: empty arrays should still be wrapped.
- **Sidebar layout regression**: Simulate adding 50+ projects, verify the sidebar remains scrollable without layout breakage. Verify the "More" nav item does not overflow or push content offscreen. Test rapid navigation between projects while the list is scrolled.
- **Agent heartbeat recovery**: Simulate heartbeat loss by pausing the agent worker for >120 seconds. Verify auto-recovery triggers, the agent transitions back to healthy status, and error counters reset to zero. Test the manual restart endpoint (`POST /api/agents/{id}/restart`) and verify it returns 200 with cleared state. Test rapid restart calls to verify idempotency.
- **Project CRUD via context menu**: Create a project, then pause it via API (`PATCH /api/projects/{id}` with `is_paused: true`). Verify `is_paused` persists and the project stops generating agent work. Resume and verify work resumes. Delete the project and verify cascading cleanup (tasks, findings, sessions removed). Test deleting a paused project.
- **Team mode toggle persistence**: Toggle team mode on via Settings API, verify `.env` contains `TEAM_MODE=true`. Toggle off, verify `.env` updated. Restart the server simulation and verify the persisted value is loaded correctly.
- **Document Organize streaming**: Upload 10+ documents to a project, invoke the Organize endpoint, and verify the streaming response produces valid organizational suggestions. Test with zero documents (should return a meaningful empty-state message, not an error).
- **Loops skill dropdown validation**: Create a custom loop, verify the skill picker returns the full skill catalog. Select a skill from the dropdown, save the loop, and verify the skill ID is persisted correctly. Test with an invalid/deleted skill ID — verify graceful error handling.
- **Design Brief evidence and law badges**: Generate a design brief with UX law violations, verify badges render with correct violation counts. Navigate "View violations" and verify the findings list is filtered to the correct law ID. Test with zero violations — verify no badge is shown.

### Onboarding UX & Folder Linking Simulation Scenarios
- **ViewOnboarding dismissal persistence**: Navigate to each of the 21 views, verify the onboarding banner appears on first visit. Dismiss the banner, navigate away, then return — verify the banner does not reappear (localStorage persisted). Clear localStorage manually and revisit — verify banners re-appear. Test the Settings "Reset Onboarding Hints" button — verify all 21 banner keys are cleared and banners reappear on next visit.
- **OnboardingWizard step progression**: Trigger the wizard on a fresh project. Walk through all 6 steps (welcome, LLM check, project, folder link, context, upload). Verify each step transition works, back navigation returns to the previous step, and skipping optional steps does not block completion. Test closing the wizard mid-flow and reopening — verify it resumes at the correct step or restarts gracefully.
- **Folder link and unlink**: Create a project, call `POST /projects/{id}/link-folder` with a valid local path, verify the folder is linked and `linked_folder_path` is persisted. Trigger FileWatcher and verify new files in the folder are detected. Unlink the folder, verify the watcher stops monitoring and the project's `linked_folder_path` is cleared. Test linking a non-existent path — verify a descriptive error, not a 500.
- **Cloud sync temp file filtering**: Link a folder, then create files named `document.partial`, `~$report.docx`, and `upload.tmp` in the monitored directory. Verify the FileWatcher ignores all three. Create a legitimate file (`analysis.pdf`) and verify it is detected and ingested. Test edge case: rename `document.partial` to `document.pdf` — verify the renamed file is picked up on the next watch cycle.
- **Folder linking provider types**: Test linking a Google Drive folder (mock path or mount), a Dropbox folder, and a local filesystem folder. Verify `linked_folder_type` is correctly set to `gdrive`, `dropbox`, or `local` respectively. Test switching a project's linked folder from one provider to another — verify the old watcher is stopped and the new one starts.
- **Onboarding banner content accuracy**: For each of the 21 views, verify the banner title and description match the view's purpose. Verify the chat prompt suggestion is contextually relevant (e.g., Skills view suggests a skill-related prompt, not a project prompt). Test clicking a chat prompt suggestion — verify it populates the chat input.

### Versioning & Update Simulation Scenarios
- **Version check**: Call `GET /api/updates/version`, verify returns CalVer string matching VERSION file. Call `GET /api/updates/check`, verify GitHub API response parsing. Test with no releases (404), current release (no update), older release (update available).
- **Pre-update backup**: Call `POST /api/updates/prepare`, verify backup record created, verify backup file exists on disk with correct checksums. Test with insufficient disk space (should fail gracefully).
- **CalVer ordering**: Verify `2026.03.29` < `2026.03.30` < `2026.04.01` < `2026.04.01.2` lexicographically. Test daily build number increment via `set-version.sh --bump`.

### Production Installer Simulation Scenarios
- **Dependency detection**: Call `installer::detect_dependencies()` on a fresh machine. Verify Python, Node, Ollama, LM Studio, Docker detection returns correct `detected` booleans and version strings. Test with deps installed and uninstalled.
- **NSIS install mode capture**: Run Windows installer, select "Client Only" mode, verify `$InstallMode` is "client" (not hardcoded "full"). Verify dependency page is skipped for client mode.
- **macOS DMG bundle integrity**: Build DMG, mount it, verify `Istara.app/Contents/Resources/istara/backend/` exists with all source files. Verify no `__pycache__`, `node_modules`, `.env`, or `data/` directories are included.
- **Setup wizard flow**: Launch Tauri app with no `~/.istara/config.json`. Verify setup wizard window opens. Complete all 6 steps. Verify config file is created with correct mode, LLM provider, and install dir. Verify services start after completion.
- **Uninstall data preservation**: Run Windows uninstaller, choose "Keep data" → verify `data/` directory preserved. Run again, choose "Delete" → verify `data/` removed.
- **CI/CD artifact verification**: Push to main branch, verify GitHub Actions builds both macOS DMG and Windows EXE. Push a `v*` tag, verify GitHub Release is created with both artifacts attached.

### Auth & Onboarding Simulation Scenarios
- **Fresh server registration**: Start with an empty database (no users). Call `GET /auth/team-status`, verify `{ team_mode: true, has_users: false }`. Submit a registration request, verify the first user is created with `role: "admin"`. Call team-status again, verify `has_users: true`. Attempt a second registration and verify the form is no longer offered (login mode instead).
- **Admin detection on refresh**: Log in as admin, call `GET /auth/me`, verify the response includes `role: "admin"` with the full user object. Simulate a page refresh by re-calling `/auth/me` with the same JWT — verify the admin role persists and is not downgraded to a default role.
- **Team status toggle**: Enable team mode via Settings API, verify `/auth/team-status` returns `team_mode: true`. Disable team mode, verify it returns `team_mode: false`. Test with `has_users` in both states (fresh vs populated) to verify correct boolean combinations.
- **Concurrent first-user race**: Simulate two simultaneous registration requests on a fresh server. Verify only one user is created as admin — the second request should either fail gracefully or create a non-admin user. No duplicate admin accounts should result.
- **Git cleanliness**: Verify `_creation_proposals.json` is not present in the repository working tree after a fresh clone. Verify `.gitignore` includes patterns for runtime data files (`*.json` proposals, evolution stats, UUID persona dirs).

### Feature Update — Agent Scope System Simulation Scenarios
- **Scope filtering**: Create a project-scoped custom agent, verify it only appears in agent lists when that project is active. Switch to a different project and verify the agent is absent. Switch back and verify it reappears. Test with no active project — verify the agent is not listed.
- **Promotion request flow**: Create a project-scoped agent, call `POST /agents/{id}/request-promotion`, verify 200 response and that an admin notification is created. Verify non-admin users cannot call `POST /agents/{id}/set-scope` (expect 403). Call set-scope as admin, verify the agent's scope changes to universal and it now appears in all project contexts.
- **System agent immutability**: Verify all 5 system agents have `scope='universal'` and `project_id=null`. Attempt to change a system agent's scope via set-scope — verify it is rejected or ignored. System agents must never become project-scoped.
- **Project data isolation**: Create two projects with project-scoped agents in each. Verify agents from project A do not leak into project B's agent list. Delete project A and verify its agents are cleaned up (no orphans).
- **Stale localStorage cleanup**: Simulate storing a deleted project's ID in localStorage, then trigger the login cleanup flow. Verify the stale ID is removed and the UI shows "No Project Selected" instead of referencing a ghost project.
- **DB migration idempotency**: Call `init_db()` twice in sequence. Verify the ALTER TABLE statements for `scope`, `project_id`, `is_paused`, and `owner_id` do not raise errors on the second run (try/except wrapping).

## Desktop App, Connection Strings & Installers
- **Connection string round-trip**: Admin generates a connection string via `POST /api/settings/connection-string`, verify the response is `rcl_`-prefixed and HMAC-signed. Decode the string, extract server URL + network token + JWT, verify all three fields are present and the JWT is valid. Paste the string into the "Join Server" endpoint, verify the client authenticates successfully and receives a session. Test with a tampered string (modified payload, same HMAC) — verify rejection with a clear error. Test with an expired JWT — verify rejection with an expiry-specific message.
- **Connection string token rotation**: Generate a connection string, then rotate the NETWORK_ACCESS_TOKEN via Settings API. Attempt to redeem the old connection string — verify it fails with an auth error (not a generic 500). Generate a new string after rotation — verify it works. Test that existing relay connections using the old token are disconnected and must re-authenticate.
- **Browser compute relay**: Simulate the DonateComputeToggle flow: call the toggle endpoint with a valid JWT, verify a WebSocket relay connection is established. Verify the relay node appears in the compute registry with source type "browser". Simulate LLM detection (mock LM Studio health endpoint on localhost) — verify capabilities are probed and badges populated. Toggle off — verify the relay disconnects and the node is removed from the registry. Test toggling on without a local LLM — verify a graceful "No local LLM detected" response, not an error.
- **Relay --connection-string bootstrap**: Simulate relay startup with a connection string flag: decode the string, verify HMAC validation passes, extract the server URL, and verify the relay connects to the correct WebSocket endpoint with the X-Access-Token header. Test with an invalid connection string — verify the relay exits with a descriptive error, not a crash. Test with a valid string pointing to an unreachable server — verify timeout and retry behavior.
- **Installer first-run simulation**: Simulate the dependency checker: mock missing Python/Node dependencies and verify the checker reports them with actionable install instructions. Simulate the .env wizard: verify it generates a valid .env with JWT_SECRET, DATA_ENCRYPTION_KEY, and DATA_DIR. Verify Server+Client mode starts both backend and frontend processes. Verify Client-only mode skips backend startup and prompts for a connection string.
- **Desktop app lifecycle (shell delegation architecture)**: Simulate Tauri tray interactions: tray delegates start/stop to `istara.sh` (single source of truth). Verify: Start menu item calls `istara.sh start` and label changes to `● Stop Istara Server` when ports are up. Stop calls `istara.sh stop` and label changes to `○ Start Istara Server`. Toggle Compute Donation on — verify relay starts, config saves, confirmation dialog appears. Toggle off — verify relay stops, config saves, dialog appears. Click LM Studio when running — verify status dialog with donation toggle option. Click when not running — verify LM Studio launch offer. Check for Updates — verify three-tier check (Tauri updater, git tags, GitHub releases) always shows result dialog. Quit — verify only relay stopped (backend/frontend persist via PID files). Simulate Client-only mode with no connection string — verify app opens LoginScreen "Join Server" tab.

### Installation & First-Run Simulation
- **Shell installer**: Verify the one-liner installs all dependencies, creates venv, builds frontend, generates .env, writes config.json, and adds `istara` to PATH. Test on clean machines (no Python/Node) and machines with existing installs. Verify the ERR trap shows line numbers on failure.
- **CLI lifecycle**: `istara start` → verify backend PID is alive + health endpoint responds within 15s. `istara stop` → verify both PIDs cleaned up + ports freed. `istara status` → verify output matches actual process state. Test: start, kill backend manually, verify `istara status` detects the dead process and cleans up the PID file.
- **Login UX flow**: Local mode — verify name-only screen appears, "Get Started" works, JWT is issued. Team mode with no users — verify registration screen auto-appears, first user gets admin role. Server unreachable — verify error screen with `istara start` instructions. Team mode with users — verify login/register/join toggles work.
- **Uninstaller safety**: Run uninstaller on a test install. Verify it stops processes, removes files, cleans PATH, removes LaunchAgent. Verify "uninstall" confirmation is required (not just Y/n). Verify optional dependency removal defaults to No.
- **Tray app integration**: Install via shell one-liner (Step 8), verify Istara.app appears in /Applications. Launch, verify tray icon appears with menu. Start server via tray — verify it calls `istara.sh start` and menu label updates to `● Stop`. Stop via tray — verify it calls `istara.sh stop` and label updates to `○ Start`. Verify Compute Donation shows confirmation dialog. Verify Check for Updates shows result dialog. Verify Quit only stops relay (not backend/frontend). Verify ANSI codes from script output are stripped in error dialogs.
- **Guided tour flow**: Simulate the full 10-step admin tour: folder input → project creation → team mode toggle → connection string generation → file prompt → context fill → tasks view → LLM check (mock connected/disconnected states) → chat arrival. Verify step progression, conditional skipping (non-admin skips steps 2-4, existing projects skip 0-1), localStorage persistence across refresh, and skip functionality.
- **Member tour flow**: Simulate a team member joining via connection string on login screen. Verify the pre-login guidance banner, join mode help text, post-validation account creation. After login, verify tour starts at step 5 (skipping project + team), with member-specific popover text.

## Limitations
- Cannot test actual browser rendering (tests are API-level, not visual)
- Cannot simulate real user mouse movements or visual scanning patterns
- Cannot test offline behavior or network interruption recovery
- Cannot measure actual user satisfaction or emotional response
- Simulation data must be cleaned up to avoid polluting the real database
- Cannot test authentication flows (operates with system-level API access)

## Research Integrity Workflow Simulation
- **End-to-End Thematic Analysis**: Simulate the full research integrity pipeline: upload data -> run thematic analysis skill -> review generated codes -> approve/reject each code -> check convergence report. Verify each stage transitions correctly and data persists between steps.
- **Validation Gate Testing**: Submit intentionally low-quality or malformed data (empty transcripts, nonsense text, duplicate entries) and verify the system blocks or flags it appropriately. Confirm validation error messages are actionable and the system does not proceed with invalid data.
- **Codebook Versioning**: Create an initial codebook via analysis, then modify codes (rename, merge, split, delete). Verify a new codebook version is created with correct version number, the previous version remains accessible, and diffs between versions accurately reflect the changes made.
- **Evidence Chain Traceability**: After analysis completes, trace a recommendation from the final report (L4) back through synthesis (L3), analysis (L2), and down to the original source text nugget. Verify source_location references are correct and point to actual content in the uploaded data.
- **Report Convergence**: Run 2+ analysis methods on the same dataset, then verify L3 synthesis is auto-created from the L2 analyses. Check that the convergence pyramid populates correctly, conflicting findings across methods are surfaced, and the final L4 report integrates all L3 syntheses.

### InteractiveSuggestionBox & UI Fixes Simulation (v2026.04.01)
- **InteractiveSuggestionBox lifecycle**: Open Documents, click Organize, verify session created via sessionsApi.create(), verify streaming chunks with auto-scroll, type follow-up reply, verify sends to same session, click "Continue in Chat", verify navigation to Chat view with correct session.
- **Sync toast**: Click Sync in Documents, verify toast with count. Verify auto-dismiss after 5s.
- **Notification bell badge**: Create notification via API, verify badge shows "1". Mark read, verify disappears. Create 100+, verify "99+".
- **API error extraction**: POST /auth/users with invalid email, verify readable error not "[object Object]".
- **EnsembleHealth scroll**: Navigate to Ensemble Health, verify scrollable when content exceeds viewport.

### Chat UX & Ensemble Simulation (v2026.04.01.3)
- **Chat markdown**: Send message with ## headers, **bold**, code blocks. Verify rendered as HTML, not raw text.
- **File chips**: Select files, verify chips appear. Remove one, verify removed. Send, verify all upload.
- **Document picker**: Click FolderOpen, search documents, select one, verify purple chip. Send message, verify reference included.
- **Task instructions**: Create task with "Specific Instructions" filled. Run agent. Verify instructions appear in the LLM prompt.
- **Ensemble validation**: After agent processes task, verify task.validation_method is set. Check MethodMetric has a new record.
- **CSV classification**: Upload survey CSV (with SUS, rating columns). Verify classified as survey_data, not interview_transcript.
