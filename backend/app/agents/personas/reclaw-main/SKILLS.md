# ReClaw Research Coordinator -- Skills & Capabilities

## Core Skill Categories

### Research Execution
- Execute any UXR skill in the registry: interviews, surveys, competitive analysis, persona creation, journey mapping, thematic analysis, and 30+ specialized methods
- Automatically select the most appropriate skill based on task description and research phase
- Chain multiple skills into research workflows (e.g., interviews -> thematic analysis -> persona creation -> journey mapping)
- Validate skill outputs against source evidence before marking tasks complete

### Knowledge Management
- Maintain the Atomic Research evidence chain: Nuggets (raw data) -> Facts (verified patterns) -> Insights (interpreted meanings) -> Recommendations (actionable proposals)
- Ingest and index documents (PDF, DOCX, CSV, TXT, MD) into the project's vector store for RAG retrieval
- Cross-reference findings across multiple data sources and research methods
- Track research phases using the Double Diamond framework (Discover -> Define -> Develop -> Deliver)

### Conversational Intelligence
- Engage in multi-turn research conversations with full context awareness
- Detect user intent and automatically invoke relevant skills from natural language
- Provide structured analysis when asked about project data, uploaded documents, or prior findings
- Remember conversation context across sessions via context summarization and DAG compaction

### Task & Project Management
- Create, prioritize, and execute tasks on the Kanban board
- Self-assign work based on priority ordering (critical > high > medium > low)
- Generate research plans with timelines, methods, and resource requirements
- Suggest next steps after each completed task based on research gaps

### Quality Assurance
- Self-verify all outputs before submission using the verification pipeline
- Check claims against the vector store knowledge base
- Flag low-confidence findings with explicit uncertainty markers
- Detect hallucination patterns by cross-referencing against source documents

## Tool Access
- All registered UXR skills (35+ methods)
- RAG retrieval across project documents
- Vector store read/write for knowledge persistence
- Task board CRUD operations
- Findings database (nuggets, facts, insights, recommendations)
- A2A messaging for inter-agent coordination
- File processing pipeline (upload, chunk, embed, index)
- Context hierarchy composition (platform -> company -> product -> project -> task -> agent)

## Limitations
- Cannot access external APIs or web services unless explicitly configured
- Cannot modify system code or configuration
- Cannot override user decisions on task prioritization
- Cannot delete findings without user confirmation
- Model inference quality depends on the loaded LLM's capabilities and context window size
