# Conductor Prompt: Istara vs Pi ReAct Engine Comparison

You are one of three architects in a planning-only Build Stream conductor round.

The owner wants a durable plan, saved under `comparison-Istara-pi/`, for evaluating whether Pi can replace Istara's agentic management core: ReAct/tool loops, planner/executor behavior, model management, SDK/process integration, session/harness mechanics, and channel-facing agent integrations.

## Scope

Compare Istara against the three core Pi packages in the `earendil-works/pi` monorepo:

- `@earendil-works/pi-coding-agent`: `https://github.com/earendil-works/pi/blob/main/packages/coding-agent`
- `@earendil-works/pi-agent-core`: `https://github.com/earendil-works/pi/blob/main/packages/agent`
- `@earendil-works/pi-ai`: `https://github.com/earendil-works/pi/blob/main/packages/ai`

Do not treat `pi-review` or `pi-chat` as core comparison targets. They may be cited only as
Pi ecosystem references for review workflows, chat/sandboxing, channel memory, or remote
control patterns. `pi-tutorial` is optional prompt-adherence reference material only.
`pi-website` is archived and excluded from runtime comparison.

## Required Evaluation Dimensions

Plan evaluations and tests for:

- Tool calling.
- Integration with each Istara feature, with feature-specific success criteria.
- Final output quality.
- Quality by each step of Istara's research spine.
- Memory load.
- Tokens spent per step and total tokens.
- Number of tool calls versus quality of output.
- Skills adherence.
- System prompt adherence.
- A2A success on task, especially fewer interactions and/or tool calls with higher output quality.
- Agentic management and orchestration.
- Model management and provider routing.
- Feasibility of replacing Istara's full agentic management core with Pi, not merely augmenting one loop.
- Feasibility of reconnecting all Istara product features to Pi through adapters/canonical tools while preserving feature behavior.
- Feasibility of using Pi-supported channels where Istara uses channel integrations.
- Feasibility of using Pi as an independently updateable dependency or sidecar so Istara
  adapts to selected Pi versions without embedding Pi internals or forcing broad feature rewrites.
- Best practices to adopt if Pi performs better.

## Hard Constraints

- First round only: create the testing lab and plan. Do not start testing.
- Do not modify Istara code.
- All written artifacts must live under `comparison-Istara-pi/`.
- Use Compass Forge read-only inspection for Istara code graph and relationships.
- Use GitHub/API/source inspection for Pi; avoid large clones unless absolutely necessary.
- Do not use local models.
- Do not run cloud LLM tests until the owner provides API instructions.
- Keep storage nimble.

## Expected Architect Outputs

Each architect must return technical Markdown suitable for incorporation into an academic-style Build Stream document:

- Scope and assumptions.
- Surfaces inspected.
- Feature criteria and measurement plan.
- Experimental design.
- Evidence model and metrics.
- Risks, threats to validity, and open questions.
- Recommended next tasks.

## Architect Lenses

Architect A: Istara internals and existing evaluation assets.

Architect B: Pi architecture and replacement feasibility.

Architect C: evaluation methodology, metrics, evidence collection, and academic article structure.
