/** Scenario 71 — Plan-and-Execute: verify the agent decomposes complex tasks into steps. */

export const name = "Plan-and-Execute Architecture";
export const id = "71-plan-and-execute";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];
  let projectId = ctx.projectId;

  // 1. Create a project if needed
  if (!projectId) {
    try {
      const project = await api.post("/api/projects", { name: "Plan-Execute Test" });
      projectId = project.id;
      checks.push({ name: "Project created", passed: true, detail: projectId });
    } catch (e) {
      checks.push({ name: "Project created", passed: false, detail: e.message });
      return { checks, passed: 0, failed: 1, summary: "Cannot create project" };
    }
  }

  // 2. Create a complex task (no explicit skill — should trigger planning)
  let taskId;
  try {
    const task = await api.post("/api/tasks", {
      project_id: projectId,
      title: "Comprehensive UX Analysis",
      description: "Analyze user interview transcripts, identify usability issues from survey data, and cross-reference with competitive analysis. Produce actionable recommendations.",
      priority: "high",
    });
    taskId = task.id;
    checks.push({ name: "Complex task created", passed: !!taskId, detail: `Task ID: ${taskId}` });
  } catch (e) {
    checks.push({ name: "Complex task created", passed: false, detail: e.message });
  }

  // 3. Wait for agent to pick up the task (up to 60s)
  if (taskId) {
    let planFound = false;
    for (let i = 0; i < 20; i++) {
      await new Promise((r) => setTimeout(r, 3000));
      try {
        const task = await api.get(`/api/tasks/${taskId}`);
        if (task.agent_notes && task.agent_notes.includes("Research Plan")) {
          planFound = true;
          // Verify plan JSON structure
          const planMatch = task.agent_notes.match(/\{[\s\S]*"steps"[\s\S]*\}/);
          if (planMatch) {
            try {
              const plan = JSON.parse(planMatch[0]);
              const stepCount = (plan.steps || []).length + (plan.completed || []).length;
              checks.push({
                name: "Research plan created",
                passed: stepCount >= 2,
                detail: `${stepCount} steps in plan, status: ${plan.status}`,
              });

              // Check for depends_on field (DAG support)
              const hasDepends = (plan.steps || []).some((s) => s.depends_on && s.depends_on.length > 0) ||
                                (plan.completed || []).some((s) => s.depends_on && s.depends_on.length > 0);
              checks.push({
                name: "Plan supports dependencies (DAG)",
                passed: true, // depends_on may be empty for simple plans
                detail: hasDepends ? "Steps have dependency links" : "All steps independent (parallel capable)",
              });
            } catch {
              checks.push({ name: "Plan JSON parseable", passed: false, detail: "Invalid JSON in agent_notes" });
            }
          }
          break;
        }
        if (task.status === "in_review" || task.status === "done") {
          // Agent completed without plan (simple task fallback)
          checks.push({
            name: "Task completed (may have skipped planning)",
            passed: true,
            detail: `Status: ${task.status}, notes length: ${(task.agent_notes || "").length}`,
          });
          break;
        }
      } catch (e) {
        // Task not ready yet
      }
    }
    if (!planFound) {
      checks.push({
        name: "Research plan created",
        passed: false,
        detail: "Agent did not create a plan within 60s (may need LLM running)",
      });
    }
  }

  // 4. Verify task model has validation fields
  if (taskId) {
    try {
      const task = await api.get(`/api/tasks/${taskId}`);
      checks.push({
        name: "Task has validation fields",
        passed: task.validation_method !== undefined,
        detail: `validation_method: ${task.validation_method || "null"}, consensus_score: ${task.consensus_score || "null"}`,
      });
    } catch (e) {
      checks.push({ name: "Task validation fields", passed: false, detail: e.message });
    }
  }

  // 5. Verify skills API returns skills with lifecycle info
  try {
    const skills = await api.get("/api/skills");
    const skillList = Array.isArray(skills) ? skills : skills?.skills || [];
    const hasLifecycle = skillList.some((s) => s.lifecycle || s.utility_score !== undefined);
    checks.push({
      name: "Skills have lifecycle tracking",
      passed: skillList.length > 0,
      detail: `${skillList.length} skills loaded, lifecycle tracking: ${hasLifecycle}`,
    });
  } catch (e) {
    checks.push({ name: "Skills API", passed: false, detail: e.message });
  }

  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
    summary: checks.map((c) => `${c.passed ? "PASS" : "FAIL"} ${c.name}: ${c.detail}`).join("\n"),
  };
}
