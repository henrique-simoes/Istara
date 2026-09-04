"""Technology metadata and copy for Istara capability explanation pages."""

TECH_PAGES = {
    "grounded-chat": {
        "title": "Intelligent Grounded Chat",
        "eyebrow": "Core Swarm Capability",
        "summary": "Source-bounded conversational reasoning and multi-turn verification systems.",
        "image": "tech_chat.png",
        "code_refs": [
            "backend/app/api/routes/chat.py",
            "backend/app/services/research_validity_service.py",
        ],
        "content": """
<h2>User & Researcher Perspective</h2>
<p>Intelligent Grounded Chat enables researchers to interact with primary source repositories (such as video transcripts, survey responses, and session logs) using standard conversational prompts. It operates on a strict evidence backlink model: every assertion or quote rendered in chat is accompanied by clickable trace anchors linking directly to the exact source span, eliminating manual verification overhead.</p>
<h3>Operational Workflows & Intent</h3>
<ul>
  <li><strong>Evidence Tracking:</strong> Researchers click trace markers within assistant responses to instantly inspect and verify the raw text blocks behind synthesized insights.</li>
  <li><strong>Query Refinement:</strong> Conversational queries can reference active project contexts, primary nodes, or accepted code structures, allowing precise thematic deep-dives.</li>
</ul>

<h2>Engineering & Architecture Perspective</h2>
<p>The Grounded Chat subsystem is exposed via the API endpoint <code>/api/chat</code> and handled by <code>backend/app/api/routes/chat.py</code>. It enforces local vector/keyword RAG context lookup utilizing a non-bypassable context routing DAG.</p>
<h3>Granular Technical Data Flow</h3>
<ol>
  <li><strong>Payload Reception:</strong> User queries are POSTed to <code>/api/chat/message</code>, carrying active <code>project_id</code>, session identifiers, and optional vector search steering weights.</li>
  <li><strong>Context Routing DAG:</strong> The routing engine dynamically schedules parallel tasks: a LanceDB vector similarity query using local embedding caches, and an exact-match keyword lookup using BM25.</li>
  <li><strong>Reciprocal Rank Fusion (RRF):</strong> Results are blended to generate the precise top-N context blocks, ensuring high semantic recall and absolute symbolic precision.</li>
  <li><strong>Research Spine Validation:</strong> Prompt assembly binds context blocks into strict system boundary envelopes, forcing the model to cite raw lines and blocking any output not grounded in the retrieved spans.</li>
</ol>

<h2>Technical Documentation Approach</h2>
<p>Istara's chat services operate under strict security boundaries aligned with OWASP Top 10 for GenAI Applications. All retrieval prompts must protect project-scoped borders; fallback to global system context is prohibited unless explicitly authorized. The underlying data pathways are governed by <code>backend/app/services/research_validity_service.py</code>.</p>
<h3>Compliance & Quality Invariants</h3>
<ul>
  <li><strong>Scope Separation:</strong> Chat routers must explicitly reject query execution if <code>project_id</code> lacks researcher-level authorization checks.</li>
  <li><strong>Grounded Verification:</strong> Responses that fail post-generation trace verification are flagged in database records to protect against silent hallucination leakage.</li>
</ul>

<h2>Scientific Foundations & Bibliography</h2>
<p>Grounded Chat relies on peer-reviewed, state-of-the-art frameworks for context retrieval and hallucination mitigation:</p>
<ul>
  <li><strong>Retrieval-Augmented Generation:</strong> <em>Lewis et al. (2020)</em> — "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks" <em>NeurIPS 2020</em>. Establishing source-bounded prompt synthesis.</li>
  <li><strong>Hierarchical Summarization:</strong> <em>Chen et al. (2023)</em> — "Walking Down the Memory Maze: Beyond Context Limit through Interactive Reading" <em>arXiv:2310.05029</em>. MemWalker DAG-based multi-turn reading.</li>
  <li><strong>Prompt Injection Context:</strong> <em>Pan et al. (2024)</em> — "From RAG to Prompt RAG: Revisiting Retrieval-Augmented Generation for Long-Context Language Models" <em>ACL 2024</em>.</li>
</ul>
""",
    },
    "ux-skills": {
        "title": "53+ UX Research Skills",
        "eyebrow": "Core Swarm Capability",
        "summary": "Structured Double Diamond UX evaluation workflows and skill runner execution harnesses.",
        "image": "tech_skills.png",
        "code_refs": [
            "backend/app/skills/skill_manager.py",
            "backend/app/skills/registry.py",
        ],
        "content": """
<h2>User & Researcher Perspective</h2>
<p>53+ UX Research Skills provides a sandboxed, robust suite of predefined execution workflows structured around the classic Double Diamond product design stages (Discover, Define, Develop, Deliver). Researchers can execute heuristic audits, SUS usability score calculations, card sorting analyses, competitive grids, or thematic transcript tagging through simple commands, receiving structured, audit-ready data tables.</p>
<h3>Operational Workflows & Intent</h3>
<ul>
  <li><strong>Double Diamond Guided Research:</strong> Skills are classified logically to guide teams through discovering problems, defining opportunities, developing prototypes, and delivering validated specs.</li>
  <li><strong>Heuristic Audits:</strong> Researchers trigger automated audits evaluating design screenshots or prototypes against established user experience principles.</li>
</ul>

<h2>Engineering & Architecture Perspective</h2>
<p>The Skill registry is located in <code>backend/app/skills/registry.py</code> and managed by <code>backend/app/skills/skill_manager.py</code>. Executed skills run in isolated local subprocesses or sandboxed threads to ensure resource governance.</p>
<h3>Granular Technical Data Flow</h3>
<ol>
  <li><strong>Trigger:</strong> An agent or researcher dispatches a skill execution command carrying input arguments and target sources.</li>
  <li><strong>Parameters Validation:</strong> The Skill Manager loads the skill's JSON schema, sanitizes inputs, and verifies project permissions.</li>
  <li><strong>Isolated Execution:</strong> The skill runs within a resource-governed runner, catching memory exhaustion errors and keeping track of API call tokens.</li>
  <li><strong>Result Registration:</strong> Output findings, nuggets, or qualitative codes are registered under provisional states within the Research Spine.</li>
</ol>

<h2>Technical Documentation Approach</h2>
<p>UX Skills follow the Memento Skill creation and prompt-evolution protocol. All skill specifications are version-controlled and dynamically loaded. When a skill proposes prompt optimizations, the proposal must run through validation benchmarks.</p>
<h3>Compliance & Quality Invariants</h3>
<ul>
  <li><strong>Process Sandbox:</strong> Skills cannot modify filesystem areas outside of the designated project workspace.</li>
  <li><strong>Self-Evolution Controls:</strong> Prompt variations generated via meta-heuristics are locked under 'Provisional' flags until approved by human administrators.</li>
</ul>

<h2>Scientific Foundations & Bibliography</h2>
<p>Our UX evaluation engines are built on classic design methodologies and cognitive psychology laws:</p>
<ul>
  <li><strong>Design Principles Checklist:</strong> <em>Yablonski, J. (2020)</em> — <em>Laws of UX: Design Principles for Persuasive and Ethical Products</em>. O'Reilly Media. Informs our automated compliance checks and usability auditing.</li>
</ul>
""",
    },
    "evolving-agents": {
        "title": "Self-Evolving Agents & Personas",
        "eyebrow": "Core Swarm Capability",
        "summary": "Memento runtime agent evolution factory and ReasoningBank process memory engines.",
        "image": "tech_swarm.png",
        "code_refs": [
            "backend/app/core/agent_factory.py",
            "backend/app/core/meta_hyperagent.py",
        ],
        "content": """
<h2>User & Researcher Perspective</h2>
<p>Self-Evolving Agents & Personas introduces specialized agent personas (Cleo, Sentinel, Pixel, Sage, Echo) acting as active collaborators. Rather than static entities, these agents dynamically learn from process memory and human feedback. Researchers can inspect an agent's active memory graph, direct its expertise focus, or authorize the creation of custom role personas on the fly.</p>
<h3>Operational Workflows & Intent</h3>
<ul>
  <li><strong>Collaborative Research Swarms:</strong> Swarms run parallel tasks, delegating transcripts reading to Echo, design audits to Pixel, and security-compliance to Sentinel.</li>
  <li><strong>Expertise Evolution:</strong> Researchers review skill proposals and steering adjustments proposed by agents based on prior task success.</li>
</ul>

<h2>Engineering & Architecture Perspective</h2>
<p>Agents are dynamically instantiated via the Memento Agent Factory at <code>backend/app/core/agent_factory.py</code>. Process memory and execution loops are governed by the Meta-Hyperagent at <code>backend/app/core/meta_hyperagent.py</code> and logged in the <code>ReasoningBank</code>.</p>
<h3>Granular Technical Data Flow</h3>
<ol>
  <li><strong>Orchestration Dispatch:</strong> The agent factory reads task context and spins up a specific agent model with scoped permissions and custom system prompts.</li>
  <li><strong>Trajectory Log:</strong> The agent's reasoning chain, tool actions, and intermediate results are streamed directly into the <code>ReasoningBank</code> memory bank.</li>
  <li><strong>Capability Gap Detection:</strong> The Meta-Hyperagent parses the trajectory log; if failures persist, it drafts a Memento skill patch or specialized subagent outline.</li>
  <li><strong>Regulated Promotion:</strong> Updated prompts are verified against local policy constraints before deployment.</li>
</ol>

<h2>Technical Documentation Approach</h2>
<p>Agent autonomy is strictly restricted under the Self-Improvement Governance Contract (<code>docs/architecture/self-improvement-governance-contract.md</code>). Agents are structurally blocked from executing shell commands or database mutations outside of their scoped workspace.</p>
<h3>Compliance & Quality Invariants</h3>
<ul>
  <li><strong>Workspace Scoping:</strong> Every subagent is spawned in a project-scoped sandbox with inherited or branched storage limits.</li>
  <li><strong>Prompt Safety Checks:</strong> Prompt modifications must pass regression tests to ensure no degradation in security standards or operational safety limits.</li>
</ul>

<h2>Scientific Foundations & Bibliography</h2>
<p>The self-evolution engine is backed by foundational research in multi-agent orchestration and reasoning memories:</p>
<ul>
  <li><strong>Metacognitive Skill Evolution:</strong> <em>Zhou et al. (2026)</em> — "Memento-Skills: Let Agents Design Agents" <em>arXiv:2603.18743</em>. Distills the foundational pattern of agents identifying capability gaps.</li>
  <li><strong>Recursive Self-Modification:</strong> <em>Zhang et al. (2026)</em> — "Hyperagents: DGM-H Metacognitive Self-Modification for Cross-Domain Transfer and Recursive Improvement" <em>arXiv:2603.19461</em>.</li>
  <li><strong>Reasoning Memory Scale:</strong> <em>Ouyang et al. (2026)</em> — "ReasoningBank: Scaling Agent Self-Evolving with Reasoning Memory" <em>arXiv:2509.25140</em>. Tracks failed and successful loops.</li>
</ul>
""",
    },
    "compute-swarm": {
        "title": "Collaborative Compute Swarm",
        "eyebrow": "Core Swarm Capability",
        "summary": "Shared local model processing relays and WebSocket-based collaborative GPU/CPU pooling.",
        "image": "tech_relay.png",
        "code_refs": [
            "backend/app/core/compute_registry_invocation.py",
            "backend/app/api/websocket.py",
        ],
        "content": """
<h2>User & Researcher Perspective</h2>
<p>Collaborative Compute Swarm allows teams to run heavyweight AI models locally by pooling their computers' GPU and CPU power. Instead of sending sensitive qualitative data to third-party cloud servers, researchers contribute their idle hardware resources via a secure network, enabling fast, zero-cost, offline qualitative analysis.</p>
<h3>Operational Workflows & Intent</h3>
<ul>
  <li><strong>Local Computing Pool:</strong> Researchers enable compute donation in their settings to contribute VRAM or CPU threads when idle.</li>
  <li><strong>Swarm Model Routing:</strong> Heavy embedding or inference tasks are automatically routed to the fastest online donor in the office, eliminating individual hardware bottlenecks.</li>
</ul>

<h2>Engineering & Architecture Perspective</h2>
<p>Inference distribution and WebSocket pooling are governed by <code>backend/app/core/compute_registry_invocation.py</code> and routed through the real-time events portal in <code>backend/app/api/websocket.py</code>.</p>
<h3>Granular Technical Data Flow</h3>
<ol>
  <li><strong>Connection Registration:</strong> Donor nodes authenticate and register their hardware profile (VRAM, compute cores, and supported models) over WebSocket.</li>
  <li><strong>Task Queueing:</strong> An active RAG or coding task requests inference; the compute scheduler checks the online donor registry and selects the optimal node.</li>
  <li><strong>Request Tunneling:</strong> The prompt payload is securely transmitted over the WebSocket connection to the designated donor node.</li>
  <li><strong>Failover Recovery:</strong> If a donor node disconnects or times out mid-request, the scheduler automatically flags the failure and reroutes the request to a fallback node.</li>
</ol>

<h2>Technical Documentation Approach</h2>
<p>Compute Swarm nodes communicate over encrypted connections. Task validation processes ensure that no model weights or user-provided prompt data can be permanently cached or disclosed on donor nodes.</p>
<h3>Compliance & Quality Invariants</h3>
<ul>
  <li><strong>Zero-Retention Policy:</strong> Nodes processing swarm inference must discard all processed prompt states immediately after sending results.</li>
  <li><strong>Hardware Safeguards:</strong> Compute donation profiles are restricted under user-configured temperature and resource utilization limits.</li>
</ul>

<h2>Scientific Foundations & Bibliography</h2>
<p>Distributed model inference is inspired by collaborative research networks and decentralized GPU pooling protocols:</p>
<ul>
  <li><strong>Collaborative Inference:</strong> <em>Borzunov et al. (2022)</em> — "Petals: Collaborative Inference and Fine-tuning of Large Models" <em>arXiv:2209.01188</em>. Explores peer-to-peer VRAM pooling.</li>
  <li><strong>Internet-Scale Distribution:</strong> <em>Borzunov et al. (2023)</em> — "Distributed Inference and Fine-tuning of Large Language Models Over the Internet" <em>NeurIPS 2023</em>.</li>
</ul>
""",
    },
    "hybrid-rag": {
        "title": "Hybrid RAG + Graph RAG",
        "eyebrow": "Technical Architecture",
        "summary": "Blended vector-symbolic knowledge retrieval and network relationship traversal systems.",
        "image": "tech_rag.png",
        "code_refs": [
            "backend/app/core/embedding_cache.py",
            "backend/app/services/research_validity_service.py",
        ],
        "content": """
<h2>User & Researcher Perspective</h2>
<p>Hybrid RAG + Graph RAG combines the strengths of deep semantic vector searches and exact word matches to retrieve qualitative research. By traversing a network graph connecting primary sources, extracted codes, nuggets, facts, and tasks, it provides highly cohesive summaries that reconcile divergent research inputs without losing context.</p>
<h3>Operational Workflows & Intent</h3>
<ul>
  <li><strong>Relationship Traversal:</strong> Researchers explore qualitative connections (e.g. how a specific task relates to a user complaint and an academic paper recommendation).</li>
  <li><strong>Lossless Context Retrieval:</strong> Prevents semantic drift by combining vector queries with symbolic keyword lookups for specific terms, codes, or participant names.</li>
</ul>

<h2>Engineering & Architecture Perspective</h2>
<p>RAG pipelines and vector embedding caches are managed in <code>backend/app/core/embedding_cache.py</code> and traversed via the research validity service in <code>backend/app/services/research_validity_service.py</code>.</p>
<h3>Granular Technical Data Flow</h3>
<ol>
  <li><strong>Indexing:</strong> Primary sources are split into semantic chunks, vectorized using local models, and indexed in LanceDB while simultaneously populated in a BM25 text index.</li>
  <li><strong>Retrieval Querying:</strong> A user query triggers parallel similarity (vector) and term-frequency (BM25) queries.</li>
  <li><strong>Reciprocal Rank Fusion (RRF):</strong> The query rankings are blended via Cormack's RRF algorithm to produce a consolidated list of highly relevant chunks.</li>
  <li><strong>Graph Traversal:</strong> The system expands context by querying LanceDB relational links, retrieving all parent codes, task states, and related evidence nuggets.</li>
</ol>

<h2>Technical Documentation Approach</h2>
<p>The RAG system enforces trace integrity: no synthesized assertion is reportable unless its active vector and graph paths can be traced back to accepted primary source spans.</p>
<h3>Compliance & Quality Invariants</h3>
<ul>
  <li><strong>Trace-back Enforcements:</strong> Every Graph RAG query must register its context-retrieval graph in the database to support full engineering audits.</li>
  <li><strong>Strict Isolation:</strong> LanceDB partitions must enforce cryptographic scope boundaries to prevent cross-project context leaks.</li>
</ul>

<h2>Scientific Foundations & Bibliography</h2>
<p>Our hybrid search system implements validated data retrieval and fusion techniques:</p>
<ul>
  <li><strong>Foundational RAG:</strong> <em>Lewis et al. (2020)</em> — "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks" <em>NeurIPS 2020</em>.</li>
  <li><strong>Graph-Augmented Summarization:</strong> <em>Edge et al. (2024)</em> — "From Local to Global: A Graph RAG Approach to Query-Focused Summarization" <em>arXiv:2404.16130</em>. Basis for relational network searches.</li>
  <li><strong>Ranking Fusion (RRF):</strong> <em>Cormack et al. (2009)</em> — "Reciprocal rank fusion outperforms condorcet and individual rank learning methods" <em>SIGIR 2009</em>.</li>
  <li><strong>Symbolic Search Baseline:</strong> <em>Robertson & Zaragoza (2009)</em> — "The Probabilistic Relevance Framework: BM25 and Beyond" <em>Foundations and Trends in Information Retrieval</em> 3(4).</li>
</ul>
""",
    },
    "multi-model": {
        "title": "Multi-Model Ensemble Health",
        "eyebrow": "Technical Architecture",
        "summary": "Zero-bias independent atomic coding, consensus validation, and Fleiss' Kappa scoring engines.",
        "image": "tech_reliability.png",
        "code_refs": [
            "backend/app/skills/intercoder.py",
            "backend/app/services/research_validity_service.py",
        ],
        "content": """
<h2>User & Researcher Perspective</h2>
<p>Multi-Model Ensemble Health mitigates model bias in qualitative coding. Instead of relying on a single AI's interpretation, Istara executes parallel, independent code extractions across multiple models (e.g. Cleo, Sentinel, Pixel) and computes real-time inter-coder agreement. This ensures that only high-agreement, verified qualitative codes are accepted into your research findings.</p>
<h3>Operational Workflows & Intent</h3>
<ul>
  <li><strong>Consensus Auditing:</strong> Researchers review inter-coder agreement metrics (Fleiss' Kappa and Cohen's Kappa) to identify ambiguous codes.</li>
  <li><strong>Adjudication:</strong> Divergent extractions are routed to a human reconciliation panel, converting model disagreements into high-value qualitative insights.</li>
</ul>

<h2>Engineering & Architecture Perspective</h2>
<p>Agreement calculations and independent extractions are performed in <code>backend/app/skills/intercoder.py</code> and validated in the research validity pipeline in <code>backend/app/services/research_validity_service.py</code>.</p>
<h3>Granular Technical Data Flow</h3>
<ol>
  <li><strong>Parallel Extraction:</strong> A raw text span is dispatched to N independent local model tasks.</li>
  <li><strong>Matrix Generation:</strong> A nominal rater-by-item coding matrix is constructed, mapping model identities to assigned code classifications.</li>
  <li><strong>Statistical Evaluation:</strong> The intercoder scoring engine computes Fleiss' Kappa for multi-coder agreement or Cohen's Kappa for dual-coder comparisons.</li>
  <li><strong>Reconciliation Routing:</strong> If the agreement score meets the configured threshold, the code is promoted to 'Provisional Nugget'. Otherwise, it is routed to the human Kanban board for review.</li>
</ol>

<h2>Technical Documentation Approach</h2>
<p>Model coding consensus is a core gate of the Research Spine. The system strictly forbids using simple majority voting without computing inter-coder agreement statistics first.</p>
<h3>Compliance & Quality Invariants</h3>
<ul>
  <li><strong>Independent Coding:</strong> Models are strictly blocked from seeing peer model predictions during the initial coding phase.</li>
  <li><strong>Kappa Enforcement:</strong> Coding runs with a Kappa score below 0.65 are locked and cannot be compiled into reports until resolved by a human researcher.</li>
</ul>

<h2>Scientific Foundations & Bibliography</h2>
<p>The statistical validity of our qualitative consensus coding is backed by classic inter-rater agreement standards:</p>
<ul>
  <li><strong>Inter-Rater Reliability (Fleiss' Kappa):</strong> <em>Fleiss, J. L. (1971)</em> — "Measuring Nominal Scale Agreement among Many Raters" <em>Psychological Bulletin</em> 76(5):378-382.</li>
  <li><strong>Dual-Coder Agreement (Cohen's Kappa):</strong> <em>Cohen, J. (1960)</em> — "A Coefficient of Agreement for Nominal Scales" <em>Educational and Psychological Measurement</em> 20(1):37-46.</li>
  <li><strong>Qualitative Methodology:</strong> <em>O'Connor & Joffe (2020)</em> — "Intercoder Reliability in Qualitative Research: Debates and Practical Guidelines" <em>International Journal of Qualitative Methods</em>.</li>
  <li><strong>Codebook Discipline:</strong> <em>MacQueen et al. (1998)</em> — "Codebook Development for Team-Based Qualitative Analysis" <em>Cultural Anthropology Methods</em> 10(2):31-36.</li>
  <li><strong>Mixture-of-Agents Architectures:</strong> <em>Wang et al. (2024)</em> — "Mixture-of-Agents Enhances Large Language Model Capabilities" <em>arXiv:2406.04692</em> and <em>Li et al. (2025)</em> — "Rethinking Mixture-of-Agents: Is Mixing Different Large Language Models Beneficial?" <em>arXiv:2502.00674</em>.</li>
</ul>
""",
    },
    "distributed-compute": {
        "title": "Distributed Compute & Roles",
        "eyebrow": "Technical Architecture",
        "summary": "Multi-tenant role-based access security, cryptographic passkeys, and field encryption.",
        "image": "tech_roles.png",
        "code_refs": [
            "backend/app/api/routes/auth.py",
            "backend/app/api/agent_project_scope.py",
        ],
        "content": """
<h2>User & Researcher Perspective</h2>
<p>Distributed Compute & Roles protects sensitive qualitative research through enterprise-grade cryptographic security. The system utilizes secure biometric passkeys (registered to your hardware keychain) to replace weak passwords, and enforces strict separation between researcher roles (managing coding and transcripts) and administrator roles (managing swarm connections and system diagnostics).</p>
<h3>Operational Workflows & Intent</h3>
<ul>
  <li><strong>Passwordless Passkeys:</strong> Simple, secure biometric authentication using TouchID/FaceID registered to your local keychain.</li>
  <li><strong>Workspace Segregation:</strong> Scoped project interfaces isolate client data, preventing cross-tenant information disclosure.</li>
</ul>

<h2>Engineering & Architecture Perspective</h2>
<p>Authentication and session validation are implemented in <code>backend/app/api/routes/auth.py</code> and scoped boundaries are enforced via <code>backend/app/api/agent_project_scope.py</code>.</p>
<h3>Granular Technical Data Flow</h3>
<ol>
  <li><strong>WebAuthn Challenge:</strong> The login flow requests a cryptographic challenge from <code>/api/auth/webauthn/challenge</code>.</li>
  <li><strong>Hardware Verification:</strong> The browser registers or verifies the credential via the WebAuthn API, producing a signature verified using the server's registered public key.</li>
  <li><strong>Token Guarding:</strong> Following authentication, a session token is issued and bound to the client's local IP and user-agent string.</li>
  <li><strong>AES Scoping:</strong> Sensitive connection strings and external credentials are encrypted at rest using Fernet AES-128 keys.</li>
</ol>

<h2>Technical Documentation Approach</h2>
<p>Our security design is modeled after the OWASP Application Security Verification Standard (ASVS) 5.0.0 and NIST Digital Identity guidelines, ensuring high protection for sensitive research details.</p>
<h3>Compliance & Quality Invariants</h3>
<ul>
  <li><strong>Base URL Validation:</strong> CORS policies explicitly drop websocket connections from mismatched origins.</li>
  <li><strong>Administrative Separation:</strong> Admins cannot execute SQL or LanceDB mutations within active researcher project workspaces.</li>
</ul>

<h2>Scientific Foundations & Bibliography</h2>
<p>Security architectures implement modern biometric standards and cryptographic guidelines:</p>
<ul>
  <li><strong>Identity Guidelines:</strong> <em>NIST (2025)</em> — "Digital Identity Guidelines, SP 800-63-4 and SP 800-63B-4". Outlines MFA, session, and authenticator standards.</li>
  <li><strong>Hardware Passkeys (WebAuthn):</strong> <em>W3C (2026)</em> — "Web Authentication: An API for accessing Public Key Credentials, Level 3".</li>
  <li><strong>Auth Architectures:</strong> <em>Better Auth (2026)</em> — "Security" Reference on origin validation, CSRF, and secret handling.</li>
</ul>
""",
    },
    "human-kanban": {
        "title": "Human-in-the-Loop Kanban",
        "eyebrow": "Technical Architecture",
        "summary": "Governed task execution workspace and provisional human-in-the-loop review gates.",
        "image": "tech_kanban.png",
        "code_refs": [
            "backend/app/api/routes/meta_hyperagent.py",
            "backend/app/core/agent_execution.py",
        ],
        "content": """
<h2>User & Researcher Perspective</h2>
<p>Human-in-the-Loop Kanban keeps the researcher in absolute control of all research outputs. While AI swarm agents autonomously process transcripts and tag codes in the background, all results are populated into a provisional 'In Review' queue. Nothing can be published or compiled into a final report without explicit human verification and sign-off.</p>
<h3>Operational Workflows & Intent</h3>
<ul>
  <li><strong>Reconciliation Board:</strong> Researchers drag, drop, merge, or refine proposed findings on a visual board.</li>
  <li><strong>Done-Task Gates:</strong> Tasks are promoted to the 'Approved Done' state only after a researcher explicitly verifies and locks the source evidence links.</li>
</ul>

<h2>Engineering & Architecture Perspective</h2>
<p>Task states are managed under the Meta-Hyperagent schema in <code>backend/app/api/routes/meta_hyperagent.py</code> and tracked via the runner in <code>backend/app/core/agent_execution.py</code>.</p>
<h3>Granular Technical Data Flow</h3>
<ol>
  <li><strong>Agent Execution:</strong> An agent completes a coding task and posts candidate findings to the database.</li>
  <li><strong>Provisional Staging:</strong> The findings are registered with a `provisional=True` flag and rendered on the Kanban board under review lists.</li>
  <li><strong>Human Adjudication:</strong> The researcher modifies, merges, or accepts the finding.</li>
  <li><strong>Locking Constraint:</strong> The database updates the state to `approved=True` and locks the record against automated modifications.</li>
</ol>

<h2>Technical Documentation Approach</h2>
<p>Our Human-in-the-Loop review queues follow the NIST AI Risk Management Framework to prevent agentic hallucination leakages and ensure human control.</p>
<h3>Compliance & Quality Invariants</h3>
<ul>
  <li><strong>Review Integrity:</strong> Reports compiler strictly filters out any nugget or finding that does not possess an active human-approval timestamp.</li>
  <li><strong>Immutable Locks:</strong> Approved findings cannot be edited, deleted, or updated by autonomous agent threads.</li>
</ul>

<h2>Scientific Foundations & Bibliography</h2>
<p>The review spine implements structured methodology concepts and risk frameworks:</p>
<ul>
  <li><strong>Atomic Research Methodology:</strong> <em>Sharon & Gadbaw (2018)</em> — "Atomic Research" WeWork Research Operations. Inspires our source-grounded evidence loops.</li>
  <li><strong>AI Safety Governance:</strong> <em>NIST (2023–2026)</em> — "AI Risk Management Framework 1.0" and GenAI profile resources. Governs human-in-the-loop task boundaries and telemetry tracking.</li>
</ul>
""",
    },
    "stitch-figma": {
        "title": "Stitch & Figma Interfaces",
        "eyebrow": "Technical Architecture",
        "summary": "Bidirectional design canvas node syncing and automated Google Stitch spec builders.",
        "image": "tech_handoff.png",
        "code_refs": [
            "backend/app/services/laws_of_ux_service.py",
            "backend/app/skills/registry.py",
        ],
        "content": """
<h2>User & Researcher Perspective</h2>
<p>Stitch & Figma Interfaces bridges the gap between research findings and design layouts. By connecting Figma frame layers directly to accepted qualitative nuggets, it ensures that design decisions are backed by evidence. It also integrates with the Google Stitch Model Context Protocol (MCP) server to generate structural wireframes and design specs directly from verified reports.</p>
<h3>Operational Workflows & Intent</h3>
<ul>
  <li><strong>Figma Syncing:</strong> Import Figma artboards, mapping visual layers to usability problems and accepted research codes.</li>
  <li><strong>Stitch Wireframing:</strong> Trigger Google Stitch layout synthesis to automatically draft UI wireframes built on verified user recommendations.</li>
</ul>

<h2>Engineering & Architecture Perspective</h2>
<p>Layout compliance check services reside in <code>backend/app/services/laws_of_ux_service.py</code> and the external interfaces are routed through the MCP connector in <code>backend/app/skills/registry.py</code>.</p>
<h3>Granular Technical Data Flow</h3>
<ol>
  <li><strong>Figma Canvas Ingestion:</strong> The Figma connector retrieves the component layer hierarchy via API, storing the layout tree in the local SQLite database.</li>
  <li><strong>Evidence Binding:</strong> Layers are bound to database nugget IDs, establishing a bi-directional mapping.</li>
  <li><strong>MCP Server Dispatch:</strong> The system initiates a Google Stitch tool call over the Model Context Protocol (MCP) transport channel.</li>
  <li><strong>Wireframe Synthesis:</strong> The Stitch server processes reports, maps recommendations to spatial UI layouts, and registers the wireframe specs in the design folder.</li>
</ol>

<h2>Technical Documentation Approach</h2>
<p>MCP connectivity utilizes strict authorization parameters, checking all incoming and outgoing schemas against validated MCP server trust policies.</p>
<h3>Compliance & Quality Invariants</h3>
<ul>
  <li><strong>Auth Guarding:</strong> Figma API tokens and Stitch server scopes are encrypted at rest using project-scoped Fernet keys.</li>
  <li><strong>Schema Sanitation:</strong> Outgoing tool calls are sanitized to prevent prompt injections from carrying malicious scripts to local design environments.</li>
</ul>

<h2>Scientific Foundations & Bibliography</h2>
<p>Interoperability protocols are built on verified model context standards and integration frameworks:</p>
<ul>
  <li><strong>Model Context Protocol:</strong> <em>Model Context Protocol (2025)</em> — "MCP Specification 2025-11-25" modelcontextprotocol.io. The open standard for tool and platform integration.</li>
  <li><strong>Agent-to-Agent Protocols:</strong> <em>Agent2Agent Project (2026)</em> — "Agent2Agent (A2A) Protocol Specification" a2a-protocol.org. Inspires our cross-system interoperability manifests.</li>
</ul>
""",
    },
    "grounded-decisions": {
        "title": "Grounded Decisions & Reports",
        "eyebrow": "Technical Architecture",
        "summary": "Research validity spine report compiler and source-grounded document builders.",
        "image": "tech_reports.png",
        "code_refs": [
            "backend/app/services/research_validity_service.py",
            "backend/app/api/routes/improvement_governance.py",
        ],
        "content": """
<h2>User & Researcher Perspective</h2>
<p>Grounded Decisions & Reports compiles stakeholder reports and design briefs that are mathematically grounded in raw transcript evidence. The reporting engine crawls the Research Spine, ensuring that every claim is verified and linked back to its source, creating reliable reports that stand up to engineering audits.</p>
<h3>Operational Workflows & Intent</h3>
<ul>
  <li><strong>Source-Trace Reports:</strong> Generate PDFs or Markdown documents where every insight has interactive trace linkages back to raw transcripts or survey records.</li>
  <li><strong>Rigor Validation:</strong> Review report consensus scoring, ensuring full compliance with qualitative and statistical safety constraints.</li>
</ul>

<h2>Engineering & Architecture Perspective</h2>
<p>Report generation and validity spines are operated by <code>backend/app/services/research_validity_service.py</code> and audited via the improvement governance lifecycle in <code>backend/app/api/routes/improvement_governance.py</code>.</p>
<h3>Granular Technical Data Flow</h3>
<ol>
  <li><strong>Spine Ingestion:</strong> The compiler initiates a relational search over the project database, traversing: Approved Recommendations -> Scoped Insights -> Accepted Facts -> High-Kappa Nuggets.</li>
  <li><strong>Validity Verification:</strong> The compiler validates that all nodes are fully approved by human review and contain unbroken links to raw source spans.</li>
  <li><strong>Serialization:</strong> Synthesized copy is formatted into standards-compliant Markdown, retaining citation trace brackets (e.g. `[Nugget #122]`).</li>
  <li><strong>Integrity Proof:</strong> The compiler registers a cryptographic checksum of the generated report in the validation logs.</li>
</ol>

<h2>Technical Documentation Approach</h2>
<p>Reports and decisions are validated against state-of-the-art evaluation harnesses including HELM and RAGAS parameters to verify context relevance, faithfulness, and answer correctness.</p>
<h3>Compliance & Quality Invariants</h3>
<ul>
  <li><strong>Zero-Hallucination Gate:</strong> The generation process automatically aborts if any selected finding lacks verified evidence back-links.</li>
  <li><strong>Verification Ledger:</strong> Cryptographic report hashes are logged in the verification ledger, preventing silent, unauthorized report revisions.</li>
</ul>

<h2>Scientific Foundations & Bibliography</h2>
<p>Evaluation frameworks are modeled on leading academic and safety institute benchmarks:</p>
<ul>
  <li><strong>Atomic Qualitative Chains:</strong> <em>Sharon & Gadbaw (2018)</em> — "Atomic Research" WeWork Research Operations.</li>
  <li><strong>Agentic Assessment:</strong> <em>UK AI Security Institute (2026)</em> — "Inspect AI" inspect.aisi.org.uk. Defines evaluation harnesses.</li>
  <li><strong>Language Models Evaluation:</strong> <em>Liang et al. (2022)</em> — "Holistic Evaluation of Language Models" Stanford CRFM HELM.</li>
  <li><strong>RAG Faithfulness Evals:</strong> <em>Es et al. (2023)</em> — "RAGAS: Automated Evaluation of Retrieval Augmented Generation" <em>arXiv:2309.15217</em>.</li>
</ul>
""",
    },
}
