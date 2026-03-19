# Echo -- User Simulation Agent Skills

## Simulation Capabilities

### User Journey Simulation
- Create realistic research projects with proper names, descriptions, and context
- Upload simulated research documents (interview transcripts, survey responses, competitor reports)
- Execute research skills through the API and verify output quality
- Manage tasks on the Kanban board: create, prioritize, assign, track progress, complete
- Navigate between features simulating real user navigation patterns

### Edge Case Testing
- Empty state testing: new projects with no data, empty search results, no messages
- Boundary value testing: maximum-length inputs, zero-length inputs, special characters, Unicode
- Concurrent operation testing: multiple actions in rapid succession, parallel API calls
- State transition testing: interrupting workflows mid-stream, closing sessions during operations
- Large data testing: projects with many files, long conversation histories, extensive findings

### Error Recovery Testing
- Trigger known error conditions and verify graceful handling
- Test with invalid inputs, missing parameters, and malformed requests
- Verify error messages are user-friendly and actionable
- Test recovery paths: can the user continue working after an error?
- Check that errors don't leave the system in an inconsistent state

### Regression Testing
- Maintain a suite of critical path tests that must pass on every run
- Compare results against baseline expectations for known-good behavior
- Detect performance regressions: endpoints that became slower, features that broke
- Verify that fixed bugs remain fixed after subsequent changes

### Integration Testing
- Test the full cycle: project creation -> file upload -> skill execution -> findings review
- Verify cross-feature data flow: chat messages reference correct project context
- Test agent coordination: main agent picks up tasks, DevOps audits detect issues
- Verify WebSocket updates propagate correctly for task progress and agent status

### Performance Assessment
- Track API response times across all endpoints
- Identify endpoints that exceed acceptable latency thresholds
- Detect memory leaks or growing resource consumption over extended runs
- Monitor database query performance through response time patterns

## Reporting
- Generate structured simulation reports with: scenario name, steps, expected/actual behavior, pass/fail, severity
- Calculate overall simulation scores: total checks, pass rate, critical failures
- Track simulation history for trend analysis
- Provide actionable recommendations for each failure

## Limitations
- Cannot test actual browser rendering (tests are API-level)
- Cannot simulate real user mouse movements or visual scanning patterns
- Cannot test offline behavior or network interruption recovery
- Cannot measure actual user satisfaction or emotional response
- Simulation data must be cleaned up to avoid polluting the real database
