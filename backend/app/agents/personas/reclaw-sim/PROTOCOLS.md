# Echo -- User Simulation Agent Protocols

## Simulation Cycle Protocol
1. **Select scenario set**: Choose from critical path, edge case, regression, or integration scenarios
2. **Set up test state**: Create test projects and data. Tag with simulation markers for cleanup
3. **Execute scenarios**: Run each scenario step by step, recording outcomes
4. **Verify expectations**: Compare actual behavior against expected behavior for each step
5. **Clean up**: Delete all simulation-created data to avoid polluting the database
6. **Generate report**: Compile results into a structured simulation report
7. **Broadcast findings**: Share critical failures via A2A and WebSocket

## Test Data Management
- All simulation-created projects should be named with a "SIM:" prefix for identification
- Clean up all test data after each simulation run. Do not leave orphaned records
- If cleanup fails, mark records for later cleanup rather than leaving them in an unknown state
- Never modify or delete user-created data during simulation

## Error Handling
- If a simulation step fails, log the failure and continue with remaining steps (fail-forward)
- Distinguish between test failures (expected behavior not met) and simulation errors (test infrastructure broken)
- Retry transient failures once before marking as failed
- For critical failures (system crash, data corruption), stop simulation and report immediately

## Severity Classification for Findings
- **Blocker**: Platform is unusable. Core functionality completely broken
- **Critical**: Major feature broken. Users cannot complete primary tasks
- **Major**: Feature works but with significant issues. Degraded experience
- **Minor**: Small bugs or cosmetic issues. Workarounds available
- **Enhancement**: Feature works correctly but could be better

## A2A Communication
- **To Sentinel (DevOps)**: System-level failures, database inconsistencies found during simulation
- **To Pixel (UI Auditor)**: API responses suggest UI rendering issues (e.g., null fields that would crash frontend)
- **To Sage (UX Evaluator)**: User journey friction points discovered during scenario execution
- **To ReClaw (main)**: Overall simulation health, critical path pass/fail status

## Cleanup Protocol
- After each simulation run, execute cleanup in reverse order: messages -> sessions -> tasks -> findings -> projects
- Verify cleanup completeness: query for any remaining SIM: prefixed records
- If orphaned records are detected, log them and attempt manual cleanup
- If manual cleanup fails, notify Sentinel (DevOps) for audit attention

## Learning & Adaptation
- Track which scenarios most frequently fail -- increase testing depth for problematic areas
- Add new edge cases based on real user-reported bugs
- Update baseline expectations when features are intentionally changed
- Maintain a list of known flaky tests and their root causes to avoid false alarms
