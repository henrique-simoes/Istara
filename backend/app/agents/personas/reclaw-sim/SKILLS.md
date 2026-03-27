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

## Limitations
- Cannot test actual browser rendering (tests are API-level, not visual)
- Cannot simulate real user mouse movements or visual scanning patterns
- Cannot test offline behavior or network interruption recovery
- Cannot measure actual user satisfaction or emotional response
- Simulation data must be cleaned up to avoid polluting the real database
- Cannot test authentication flows (operates with system-level API access)
