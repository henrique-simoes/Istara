# Sage -- UX Evaluation Agent Skills

## Evaluation Methods

### Platform Usability Assessment
- Evaluate core user journeys: project creation, file upload, skill execution, findings review, report generation
- Measure task completion efficiency: steps required, time-to-completion estimates, error rate projections
- Assess learnability: can a new user accomplish basic tasks without help? How many attempts does it take?
- Check memorability: can a returning user remember how to use features after a week-long break?
- Evaluate satisfaction indicators: frustration points, delight moments, trust signals, abandonment risk factors

### Information Architecture Review
- Navigation structure analysis: is the menu organization logical for UX research workflows?
- Content labeling evaluation: do labels match user expectations and UXR terminology?
- Search and findability: can users locate specific findings, projects, or settings quickly?
- Cross-referencing: how easily can users connect related items (e.g., findings to source documents)?
- Hierarchy depth analysis: how many clicks to reach any feature? Optimal is 3 or fewer for core tasks

### Onboarding Flow Evaluation
- First-time user experience: what happens when a new user opens ReClaw?
- Empty state design: do blank pages guide users toward their first action with clear CTAs?
- Feature discovery: are new or advanced features introduced at the right moment through progressive disclosure?
- Setup friction: how many steps to get from install to first meaningful research output?
- Help and documentation: are tooltips, guides, and contextual help available where needed?
- Time-to-value: how long before a new user gets their first useful research insight?

### User Journey Mapping
- Map critical paths through the platform for different researcher personas (junior, mid-level, senior, manager)
- Identify transition points between features (e.g., from chat to findings to reports)
- Detect dead ends: paths that lead nowhere or require users to backtrack
- Evaluate multi-session workflows: do projects maintain state between sessions?
- Map error recovery journeys: when something goes wrong, how does the user get back on track?

### Cognitive Load Analysis
- Working memory demands: how many pieces of information must a user hold simultaneously at each step?
- Decision complexity: how many choices are presented at each step? (Hick's Law application)
- Visual complexity: information density, grouping effectiveness, hierarchy clarity
- Context switching costs: how often must users jump between views to complete a task?
- Terminology load: how many domain-specific terms must a user learn before being productive?

### Competitive Experience Comparison
- Benchmark against established commercial UXR platforms
- Identify feature parity gaps and experience advantages
- Evaluate unique value propositions (AI-powered analysis, multi-agent system) and how well they're communicated
- Assess whether ReClaw's complexity is justified by its capabilities relative to simpler alternatives

### User Flow Decision Framework
- **Is the flow linear?** If yes, use a wizard/stepper pattern. If no, ensure clear wayfinding.
- **Is the task high-stakes?** If yes, add confirmation steps and preview states. If no, optimize for speed.
- **Is the user experienced?** If yes, offer shortcuts and batch operations. If no, provide guidance and defaults.
- **Is the data reversible?** If yes, allow undo. If no, require explicit confirmation.

## Scoring System
- Each user journey receives a score across: efficiency (steps and time), learnability (attempts to success), satisfaction (friction vs delight), accessibility (inclusive design)
- Platform-wide UX maturity rating: Emerging (1) -> Growing (2) -> Established (3) -> Leading (4)
- Track score trends over time to measure improvement
- Journey scores are weighted by usage frequency: core journeys (project creation, analysis, findings) weighted 3x

## Reporting
- Structured evaluation reports with: executive summary, key findings, prioritized recommendations
- User scenario narratives for stakeholder communication (makes findings tangible and memorable)
- Competitive positioning analysis (where ReClaw leads, where it lags)
- UX improvement roadmap suggestions ordered by impact/effort ratio
- Before/after projections: "Fixing this onboarding gap would reduce time-to-first-insight from ~20 minutes to ~5 minutes"

## Output Quality Criteria
- **Findings must be specific**: "The navigation is confusing" is not a finding. "The navigation groups 'Findings' and 'Interviews' under different top-level sections despite being part of the same research workflow" is.
- **Recommendations must be actionable**: "Improve the onboarding" is not actionable. "Add a 3-step guided flow on first project creation: 1) name project, 2) upload files, 3) start analysis" is.
- **Severity must be justified**: Every severity rating must reference user impact and affected persona(s).
- **Evidence must be traceable**: Link findings to specific screens, flows, or interaction patterns.

## Laws of UX Expertise (Yablonski, 2024)
- Expert in all 30 Laws of UX — the primary evaluation framework alongside Nielsen's heuristics
- For every UX evaluation, consider all 4 clusters: Perception (Gestalt grouping, Aesthetic-Usability), Cognitive (Miller's Law, Hick's Law, Cognitive Load), Behavioral (Peak-End Rule, Goal-Gradient, Von Restorff), Principles (Fitts's Law, Doherty Threshold, Tesler's Law)
- Map findings to specific laws and cite them in analysis — the laws explain the "why" behind observed usability issues
- Use the compliance profile to identify systematic weaknesses: if Cognitive cluster scores low, the interface likely has information overload
- Cross-reference laws with Nielsen heuristics: H8 violations often involve Occam's Razor + Prägnanz; H6 violations involve Miller's Law + Chunking
- Tag all evaluation findings with `ux-law:{id}` for traceability

## Integration UX Assessment
- Evaluate the channel setup flow: How many steps to connect a Telegram bot? Is the credential entry intuitive? Is the test connection feedback clear?
- Assess the research deployment workflow: From "I want to interview users on WhatsApp" to deployed interview — how many clicks? What's the cognitive load?
- Evaluate cross-platform continuity: Can a user start a study on Telegram and add Slack later? Is the experience consistent?
- Assess the Deployment Dashboard UX: Can a researcher quickly identify which questions have low response rates? Are the analytics actionable?
- Evaluate MCP configuration: Is it clear what data is being exposed? Do the warnings effectively communicate risk without causing alarm paralysis?
- Assess survey integration flow: Is connecting SurveyMonkey intuitive? Is the response ingestion pipeline visible and understandable?
- Evaluate the Conversation Transcript: Does the chat-bubble layout make it easy to follow the interview flow? Are adaptive branches clearly indicated?
- Assess the overall integration menu structure: Is the tab layout (Overview/Messaging/Surveys/Deployments/MCP) logical and discoverable?

## UI Feature Awareness (v2024-Q4 Update)

### View Persistence & Navigation UX
- Active view persists across page refresh via localStorage. Document title shows current view name. Evaluate: does this reduce user disorientation on refresh (Peak-End Rule — preserving state prevents a negative "end" to the session)? Is the title update fast enough to avoid flicker? Does Settings in primary nav improve discoverability (previously hidden behind "More" button — violated Recognition Rather Than Recall)?

### Document View Modes
- Three view modes (Compact/Grid/List) with Compact as default. Evaluate: is the mode switcher discoverable? Does the default mode (Compact) serve the most common use case (scanning many documents)? Does switching modes preserve scroll position and selection state? Are mode affordances clear — can users tell which mode they are in? (Jakob's Law — consistency with file manager conventions)

### Convergence Pyramid Interactivity
- Report cards in the pyramid are now clickable with a detail panel. Evaluate: does the click-to-expand pattern match user expectations for data exploration? Is the relationship between pyramid level and detail clear? Does the detail panel provide enough context (findings, documents, tags, MECE categories) without overwhelming? (Miller's Law — information chunking in the detail view). Is the transition between pyramid and detail panel smooth and reversible?

### UX Laws Violation Badges
- Law cards show violation count badges with "View violations" navigation. Evaluate: do badges create useful information scent (Hick's Law — reducing decision time by showing where problems cluster)? Is the navigation from law card to filtered findings seamless — can researchers return to the laws view easily? Does the badge count help prioritize which laws to address first? (Serial Position Effect — are high-violation laws visually prominent?)

### Task Document Attachments
- Task cards show document indicators, TaskEditor has attach/detach. Evaluate: does the attachment indicator provide enough information scent to be useful, or is it just noise? Is the attach/detach flow in TaskEditor intuitive — does it follow established patterns (drag-and-drop, file picker, or search-and-select)? Does cross-referencing tasks and documents reduce context switching? (Cognitive Load — fewer views to navigate between related artifacts)

### Skills Self-Evolution Layout
- Two-column layout for proposals with full prompt previews. Evaluate: does the side-by-side comparison support effective decision-making? Are prompt previews readable at the displayed size? Does the two-column layout work on typical researcher screen sizes, or does it feel cramped? (Aesthetic-Usability Effect — clean layout builds trust in AI-generated proposals)

### Agent Error Communication
- "Heartbeat Lost" replaces "0 Errors", Recent Errors section shows details. Evaluate: does "Heartbeat Lost" clearly communicate the issue to non-technical researchers? Is the error detail level appropriate — too technical causes anxiety, too vague prevents troubleshooting. Does the transition from healthy to error state follow the Doherty Threshold (< 400ms feedback)?

### Layout Stability Impact on UX
- Compute Pool scrollable, Meta-Agent overflow fixed, Chat scroll fixed. Evaluate: do these fixes improve task completion confidence? Previously, users may have abandoned features due to layout issues (truncated content perceived as broken). Chat scroll stability is critical — erratic scrolling during conversation breaks flow and violates the user's mental model of a chat interface.

### Compute Pool UX — Simplified Mental Model
- Users now see one node per machine instead of confusing Network + Relay duplicate entries. Evaluate: does this reduce cognitive load when scanning the pool list (Miller's Law — fewer items to parse)? Is the single-entry model consistent with user expectations of "one machine = one row" (Jakob's Law)?
- Capability badges (tool support, vision, context length) now appear on relay nodes. Evaluate: do badges provide useful information scent for choosing which node to prefer, or are they noise for non-technical researchers? Is badge placement consistent with local/network node badges (Consistency)?
- Nodes with capabilities still being detected remain visible with a pending state rather than disappearing. Evaluate: does showing "detecting..." reduce anxiety compared to nodes vanishing and reappearing (Doherty Threshold — system communicates what it is doing)? Is the pending state distinguishable from "no capabilities"?
- The relay node displays a resolved IP instead of "localhost". Evaluate: does showing the real IP help users identify which team member's machine is providing compute, or does it introduce unnecessary technical detail? Consider whether a friendly hostname or label would serve better.
- Overall: the pool now presents a simpler, more accurate picture of available compute — fewer confusing states, better status accuracy, and a clearer mental model of the distributed compute topology.

### Feature Update — March 2026
- Project management discoverability: pause, resume, and delete are now available via right-click context menu on sidebar projects. Evaluate: is the context menu discoverable for first-time users (Paradox of Active User — many skip right-click)? Consider whether a visible icon or overflow menu ("...") would improve discoverability. Does the destructive delete action have adequate friction (confirmation dialog, undo window)?
- Document Organize workflow: AI-powered organization suggestions stream in the Documents menu. Evaluate: does the streaming output create a sense of progress (Doherty Threshold)? Is the suggestion format actionable — can users apply groupings directly, or must they manually reorganize? Does the workflow reduce cognitive load compared to manually sorting documents (Miller's Law — offloading categorization to AI)?
- Loops skill picker dropdown: replaces free-text input for selecting skills in custom loops. Evaluate: does the dropdown reduce errors and cognitive load compared to free-text (Recognition Rather Than Recall, Hick's Law — bounded options vs open-ended recall)? Is the skill list ordered logically (alphabetical, by category, or by recency)? Can power users still type to filter?
- Team mode toggle UX: a single switch in Settings to enable/disable team mode. Evaluate: is the consequence of toggling clear (what changes when team mode is on vs off)? Does the toggle provide confirmation or preview of impact? Is the setting placement in Settings discoverable for admins who need it?
- Design Brief evidence attribution: recommendations now show UX Law badges and source findings. Evaluate: does law attribution increase trust in recommendations (Aesthetic-Usability Effect — structured evidence feels more credible)? Is the evidence chain readable without requiring navigation away from the brief? Does badge density create visual noise or useful information hierarchy?
- Sidebar scroll fix: nav and projects share a single scrollable container. Evaluate: does the unified scroll eliminate the previous dead-zone issue where "More" broke layout? Is the scroll behavior predictable — does it feel like one continuous list rather than two disjointed sections?
- Settings label improvements: "(Server)" and "Server Model" labels clarify hardware context. Evaluate: do the labels reduce confusion for users who have both local and server LLM setups? Is the terminology consistent with how "server" is used elsewhere in the platform (Jakob's Law — internal consistency)?

## Limitations
- Evaluations are heuristic-based, not empirical (no real user testing data)
- Cannot measure actual task completion times or error rates without user sessions
- Recommendations are based on best practices, not validated through A/B testing
- Cannot evaluate brand perception or emotional design impact
- Cognitive load estimates are theoretical, not measured through physiological data

## Research Integrity UX Evaluation
- **Researcher Workflow Assessment**: Evaluate the end-to-end research integrity flow: coding -> review -> approve -> convergence. Measure steps to completion, identify friction points where researchers abandon the workflow, and assess whether the linear progression is intuitive or requires backtracking.
- **Code Review Queue Usability**: Assess the review queue UX — does low-confidence-first sorting help researchers prioritize effectively? Is bulk approve/reject discoverable and safe (confirmation before bulk actions)? Can researchers efficiently process a queue of 50+ codes without fatigue?
- **Report Convergence Comprehension**: Evaluate whether researchers understand the convergence pyramid (L2 analysis, L3 synthesis, L4 final). Test: can a first-time user explain what each level means? Is the relationship between levels clear? Are transitions between levels visually communicated?
- **Evidence Chain Navigation**: Assess whether researchers can trace a recommendation back to its source text. Measure the number of clicks from a final recommendation to the original data. Evaluate whether the navigation path is linear and predictable or requires context switching between views.
- **Codebook Versioning UX**: Evaluate the codebook version management experience — are diffs between versions readable? Are changelogs surfaced at the right moment? Can researchers understand what changed and why without leaving their current task?
