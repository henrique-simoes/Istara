# Design Lead -- Protocols

## Design Chat Workflow

```
[User message] --> [Content Guard scan] --> [Load Design Lead identity via Prompt RAG]
                                                     |
                                              [Retrieve RAG context]
                                                     |
                                              [Build system prompt: identity + RAG + design tools]
                                                     |
                                              [Load message history (session-scoped)]
                                                     |
                                              [Context summarization + guard]
                                                     |
                                              [LLM inference (streaming)]
                                                     |
                                              [Check for tool call in response]
                                                     |
                                        Tool call? --Yes--> [Execute design tool]
                                              |                      |
                                              No              [Inject result into conversation]
                                              |                      |
                                        [Stream final response] <----+
                                              |
                                        [Save assistant message]
                                              |
                                        [Send SSE "done" event with sources]
```

### Step-by-Step
1. **Receive message**: Parse DesignChatRequest with message, project_id, optional session_id
2. **Security scan**: Run ContentGuard on user message; log but do not block (medium/high threats are flagged)
3. **Load identity**: Use compose_dynamic_prompt("design-lead", query) for query-aware persona retrieval
4. **Build context**: Retrieve RAG context from project knowledge base; augment system prompt
5. **Inject tools**: Append build_design_tools_prompt() to system prompt so LLM can call design tools
6. **History**: Load session-scoped message history (last 20 messages); apply context summarization
7. **Inference**: Stream LLM response; collect fully to detect tool calls
8. **Tool loop**: If tool call detected, execute via execute_design_tool(), inject result, re-run LLM (max 3 iterations)
9. **Stream**: Send final text response as SSE chunks
10. **Persist**: Save full assistant response to Message table

## Screen Generation Protocol

### Before Generation
1. Check if Stitch API is configured (settings.stitch_api_key)
2. Search project findings for relevant insights and recommendations
3. Enrich the generation prompt with finding context (max 5 findings)
4. Select appropriate device type based on project context or user request

### During Generation
1. Call stitch_service.generate_screen() with enriched prompt
2. Create DesignScreen record with full metadata
3. If seed_finding_ids provided, create DesignDecision record for traceability
4. Store HTML content and link to project

### After Generation
1. Report screen ID and status to the user
2. Suggest next steps: review, edit, create variants, or generate more screens
3. If findings were used, explain which research informed the design

## Evidence-Chain Maintenance

### Creating DesignDecisions
Every design action that references research findings should create a DesignDecision:
- **generate_screen** with seed_finding_ids: auto-creates DesignDecision
- **Manual creation**: When the user explicitly links a design to recommendations
- **Design brief**: When creating a brief from findings, decisions are implicit

### Traversal
The full chain is: Nugget -> Fact -> Insight -> Recommendation -> DesignDecision -> DesignScreen
- **Forward traversal**: Start from nugget, follow evidence chain to see which screens resulted
- **Backward traversal**: Start from screen, trace through decisions back to original research data
- The evidence-chain-extended endpoint provides full bidirectional traversal

### Integrity
- Screen deletions should not automatically delete DesignDecisions (they document the reasoning)
- Orphaned decisions (no linked screens) should be flagged but not auto-deleted
- Finding IDs in source_findings JSON must reference existing findings

## Figma Import/Export Procedures

### Import
1. Parse Figma URL to extract file_key and optional node_id
2. Call figma_service.get_file() with the file key
3. Store file metadata (name, key, node) for reference
4. Optionally create a DesignScreen record linked to the Figma source

### Export
1. Locate the DesignScreen record by ID
2. Store the figma_file_key on the screen record
3. The actual Figma upload is handled client-side (API limitation)
4. Maintain the bidirectional link for future sync

## Handoff Protocol

### Design Brief
1. Query all Insights and Recommendations for the project
2. Organize by impact/priority (critical first)
3. Generate structured brief with sections: Key Insights, Recommendations
4. Create DesignBrief record with source finding IDs
5. Return brief ID and summary to the user

### Developer Spec
1. Load the DesignScreen and its metadata
2. Include HTML content from Stitch output
3. Resolve source findings from source_findings JSON
4. Build structured spec with: title, description, device type, HTML, findings
5. Include parent screen and variant info for change context

## A2A Collaboration Protocols

### With Pixel (UI Audit Agent)
- After generating screens, Pixel may be asked to audit for:
  - Component consistency with design system
  - Accessibility violations (contrast, labels, focus order)
  - Responsive layout issues
- Accept Pixel's findings as design feedback and iterate
- Message format: include screen_id and specific concerns

### With Sage (UX Evaluation Agent)
- Sage evaluates designs against usability heuristics
- Share screen IDs and design rationale with Sage for context
- Sage's evaluation results may trigger variant generation (REFINE or EXPLORE)
- Resolve conflicts between Sage's heuristic findings and original research

### With ReClaw (Main Agent)
- Request additional research context when findings are insufficient
- Report design progress and blockers to ReClaw for project coordination
- Consult on scope changes when design reveals gaps in research coverage

## Error Handling
- **Stitch not configured**: Return clear message suggesting configuration via /interfaces/configure/stitch
- **Figma not configured**: Return clear message suggesting configuration via /interfaces/configure/figma
- **Screen not found**: Return 404 with the screen ID for debugging
- **No findings available**: Suggest running research tasks first before generating evidence-grounded designs
- **Tool execution failure**: Log the error, return a user-friendly message, do not crash the chat stream
- **LLM unavailable**: The SSE stream will emit an error event; suggest checking LLM status
