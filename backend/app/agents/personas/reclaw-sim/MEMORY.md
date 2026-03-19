# Echo -- User Simulation Agent Memory

## Learnings Log

### Known Issues
- Project deletion can leave orphaned sessions and messages if cascade cleanup is not triggered properly. Always verify cleanup after deletion tests
- Chat endpoint occasionally returns 500 when the LLM model is switching. Allow brief retry window after model changes
- File upload processing is asynchronous -- need to poll for completion rather than assuming immediate availability
- The send button in chat is disabled during model loading, which can cause false "button not interactive" test failures

### Test Reliability Notes
- Chat interaction tests have timing sensitivity -- the streaming response completes asynchronously. Wait for the "done" SSE event before checking results
- Agent heartbeat tests may show "stopped" status for agents that haven't had time to send their first heartbeat. Allow 60-second warm-up
- Vector store operations can fail if the embedding model is unavailable. Check LLM health before running RAG-dependent tests
- Simulation cleanup should handle the case where delete endpoints return 404 (record already cleaned up)

### Scenario Coverage
- Critical paths: project CRUD, chat messaging, task management, findings display, settings changes
- Edge cases: empty states, null inputs, long texts, special characters, rapid actions
- Integration: cross-feature data flow, agent coordination, WebSocket updates
- Regression: previously fixed bugs that must stay fixed

### Performance Baselines
- Project CRUD endpoints: < 200ms response time
- Chat message (non-streaming): < 100ms to accept the request
- File upload (small file < 1MB): < 500ms
- Skill execution: varies by skill, typically 5-30 seconds
- Findings list: < 300ms for projects with < 1000 findings
