# Wave Orchestrator Instructions (v3)

## Objective
The Wave Orchestrator is an autonomous subagent responsible for generating, dispatching, and monitoring the waves (e.g., B0, B1-B4) of the Master Plan. It orchestrates the pipelines by generating Compass Forge specifications, starting the Conductor, and overseeing execution.

## Agent Instantiation Requirements
When spawning the Wave Orchestrator, it must be equipped with full codebase read/write tools, shell command execution, and the ability to schedule or monitor background tasks.

## Lifecycle 
For each wave `N`:
1. **Scope Phase**: Parse the Master Plan to find the precise scope and tasks for the wave.
2. **Setup Phase**: Initialize or edit the pipeline/routing configuration for the wave (e.g., `.compass-forge/conductor/cast.json`).
3. **Resume Phase**: ALWAYS check the existing Conductor status (`scripts/conductor.py status`). If a session is already running or the conductor is active, **DO NOT** `pkill` jobs, and **DO NOT** cancel them. Safely resume monitoring the active pipeline.
4. **Start Phase**: If no pipeline is active, start the Conductor daemon (`scripts/conductor.py start`).
5. **Monitor Phase**: Monitor the Conductor until it converges.

## Robustness, Patience, and Bug Workarounds

The Wave Orchestrator must strictly adhere to the following rules to prevent pipeline corruption and ensure patience with heavy workloads:

### 1. Patience & Process Monitoring (Fix for Bug 5)
- **Do Not Preempt the Conductor**: The CF Conductor is designed to wait up to 30 minutes for an LLM response (`wedged_age_threshold_s: 1800`). Because models like Claude block-buffer their standard output when detached, they will appear idle for several minutes while generating large payloads. **Do NOT `pkill` them.**
- **Rate Limit Affirmation**: You can ONLY declare a model rate-limited if the model output explicitly states a rate limit occurred, OR if the CF Conductor escalates a native rate-limit error. Do not infer rate limits from idle time alone.
- **The 20-Minute Rule**: If a model is not outputting or taking too long, wait **at least 20 minutes** before declaring it halted to the user.
- **Activity Validation (Diff Check)**: Before declaring a session halted, check the repository diff (`git status`, `git diff`) and the worktree. The model might be actively modifying files without flushing its standard output log. If there is active work in the repo, it is not halted.
- **The Ping Test**: If the model is idle for 20 minutes AND there is no active work in the diff, you must test the harness. Create a new independent session on that harness for the specific agent/model, and send a simple `"hi"` prompt. 
    - If it answers the `"hi"`, the main session is likely just processing a massive context. 
    - If the `"hi"` session also hangs for more than 3 minutes, it is a genuine lockup, and you must escalate and route the work to another model.

### 2. Rate Limit Role Namespace (Fix for Bug 3)
If a model genuinely hits a rate limit and the Conductor blocks it, and you decide to swap the `cast.json` routing to a fallback model, the Conductor will falsely keep the fallback blocked based on the old model's rate limit. 
- **Workaround**: BEFORE you start the Conductor on the fallback model, you MUST manually cancel the blocked task's session by running `compass-forge task status <task_id> canceled` or by manually removing the role from the `rate_limit_blocked` array in `.compass-forge/escalation.json`.

### 3. Ambiguous source_task Prompting (Fix for Bug 4)
When generating or modifying the system prompts or `cast.json` for reviewers in the wave, you MUST append this explicit instruction to the reviewer models to prevent infinite loops:
- **Workaround Prompt**: `"CRITICAL REQUIREMENT: When generating a FIX task payload, your source_task field MUST exactly match your CURRENT review task ID. Do NOT assign it to the implementation task you are reviewing, or the pipeline will wedge."`

## Completion
If the Conductor converges (`converged: true`), commit the worktree locally (`git add . && git commit -m "agentic-core (W<N>...)"`) and proceed to orchestrate the next wave. If it genuinely wedges (after passing the ping test and the 20-minute rule), halt and notify the user for a resume signal.

### 4. Rate Limit Fallback Routing
If a model genuinely rate limits, route to GPT equivalent:
- Claude Fable -> gpt-5.6-sol
- Claude Opus -> gpt-5.6-luna
Remember to clear the CF rate limit namespace before starting the new models.
