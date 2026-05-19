export function buildChatTurns({ total = 108 } = {}) {
  const seedTurns = [
    "I am starting a new project called CareNav Renewal. Before you analyze anything, ask me the minimum clarifying questions you need as my research partner.",
    "Here is the context: we are redesigning appointment-prep coordination for care coordinators, patients, and caregivers. Summarize what you think the project is and flag assumptions.",
    "I am uploading a previous research archive. When it is ready, tell me what kinds of sources you found and what might be risky to synthesize.",
    "Please search across the uploaded interviews for evidence about trust in readiness statuses. Cite source names when you can.",
    "Use RAG/search intentionally here: tell me which retrieved sources actually changed the answer and which were noise.",
    "That is too generic. Separate staff evidence from patient/caregiver evidence and call out contradictions.",
    "Create tasks to analyze interview pain points, survey trends, diary-study friction, and support-ticket themes. Keep them reviewable.",
    "Call whichever Istara skills or tools are appropriate for this corpus, but tell me what you attempted and what returned useful evidence.",
    "What does the survey say about reminder clarity by role and language? Do not overclaim if the CSV is thin.",
    "Pull together early atomic findings as nuggets, facts, insights, and recommendations if the evidence supports them.",
    "Check whether any memento, memory, or reasoning-bank style context exists for this project and whether it should influence the next steps.",
    "Use the usability reports to compare prototype A and prototype B. I care about scan speed and source-trail trust.",
    "I want a report outline for leadership, but make it evidence-led, not a marketing narrative.",
    "Before drafting the report, reason through the evidence chain and mark any claim that needs another retrieval pass.",
    "Try fetching the NN/g service blueprinting URL from the project URL list and tell me whether it is relevant to this workflow.",
    "Create a task to evaluate caregiver permission language. Include the Portuguese and Spanish examples as context.",
    "I suspect you are mixing caregiver and coordinator needs. Please correct that and state which sources changed your mind.",
    "Create a small agent or specialist workflow if Istara supports it, then evaluate whether the handoff made the answer better.",
    "Draft a research-backed design brief for a readiness timeline screen.",
    "Now generate or request an interface concept for the readiness timeline using the available design tools.",
    "If hyperagent or governed-improvement features exist, use the safest test path to suggest one benchmark-process improvement and keep it reviewable.",
    "Open the integrations thinking: what would I need to test Telegram recruitment without a real bot token?",
    "Try a fake Telegram setup path and tell me whether the errors are useful for a researcher.",
    "Create an AURA-style deployment plan for five adaptive interview questions about appointment preparation.",
    "Simulate participant responses if the app has a local harness. If not, record exactly what is missing.",
    "Try Typeform survey creation or a developer/demo path. I do not have credentials.",
    "Try SurveyMonkey sync with a demo/fake provider setup. Classify the result honestly.",
    "Try Google Forms setup. If service account JSON is required, test validation behavior without exposing secrets.",
    "Try Figma import with a fake URL and the mock design path if one exists.",
    "Try Google Stitch or the mock screen generation flow and show me what was generated.",
    "Check ensemble, MoA, or compute-health surfaces. I want to know whether donated Gemma chat is healthy before I trust the synthesis.",
    "Set up a loop or schedule that would recheck new support tickets weekly.",
    "Check Autoresearch status and explain whether it can be tested safely in this credential-free run.",
    "Try an autoresearch or research-agent path that uses tools, but keep it bounded to this project and tell me if it refuses safely.",
    "Review the tasks currently in Review. Approve only work that is specific, grounded, and useful.",
    "For weak reviewed work, send it back with concrete instructions instead of marking it done.",
    "Give me a compact decision log: what should the team design first and why?",
    "Now challenge your own conclusion. What evidence could point the other way?",
  ];

  const followUps = [
    "Please cite the exact files you relied on for that statement.",
    "Turn that into a task with a clear review checklist.",
    "This feels vague. Rewrite it as a finding with source, evidence, implication, and confidence.",
    "What would you ask in the next participant interview to reduce uncertainty?",
    "Compare patient versus staff needs in a two-column summary.",
    "What should we not automate yet because trust is too low?",
    "Use the analytics export to sanity-check whether the qualitative pattern appears in behavior.",
    "Which recommendation has the strongest evidence and which is only a hypothesis?",
    "Ask Istara to use the reasoning bank or project memory, then verify whether the response cites current corpus evidence too.",
    "Ask for a tool-call or skill-call trace if available; otherwise record that observability gap.",
    "Stress the context window: summarize only the newest contradictory evidence without losing the original project constraints.",
    "Create a small survey question set to validate this with caregivers.",
    "What UI state should exist for stale or contradictory readiness evidence?",
    "Find any multilingual wording risk in the archive.",
    "What is the smallest prototype we could test next week?",
    "Turn the strongest insight into a design principle.",
    "Write a task for generating an executive readout slide.",
    "Review whether the source trail concept could create privacy risk.",
    "Use web context only if it adds something concrete.",
    "Check if any task is stuck in Review and needs human approval.",
    "If the result is unsupported, ask yourself what context was missing.",
  ];

  const turns = [...seedTurns];
  let i = 0;
  while (turns.length < total) {
    turns.push(followUps[i % followUps.length]);
    i += 1;
  }
  return turns.slice(0, total).map((content, index) => ({
    turn: index + 1,
    speaker: "Maya Rodrigues",
    content,
    intent: index < seedTurns.length ? "scenario-steering" : "natural-follow-up",
  }));
}

export function buildTaskPlan({ total = 60 } = {}) {
  const taskTypes = [
    ["Analyze staff interview trust signals", "Extract staff evidence about readiness-status trust, source trails, and manual overrides."],
    ["Analyze patient appointment-prep blockers", "Identify patient-facing blockers, especially required versus optional tasks."],
    ["Analyze caregiver permission confusion", "Synthesize caregiver evidence, multilingual examples, and support tickets about access boundaries."],
    ["Survey trend readout", "Quantify reminder clarity, readiness trust, NPS, and role/language differences from the survey CSV."],
    ["Usability prototype comparison", "Compare prototype A and B for scan speed, source-trail comprehension, and caregiver-safe update completion."],
    ["Diary study synthesis", "Find recurring day-by-day prep friction and emotional patterns."],
    ["Support ticket theme clustering", "Cluster support tickets into actionable product themes and severity patterns."],
    ["Design brief for readiness timeline", "Create a brief grounded in findings, with UI requirements and non-goals."],
    ["Interface generation review", "Evaluate generated readiness timeline screens for evidence fit and usability risks."],
    ["Integration setup audit", "Document credential-free setup, harness status, and graceful degradation for one integration."],
    ["RAG grounding audit", "Inspect retrieved evidence quality, source precision, false positives, and missing-source risks for one chat synthesis."],
    ["Tool and skill trace audit", "Check whether Istara exposed useful tool-call or skill-call evidence for a researcher-facing answer."],
    ["ReasoningBank and memento audit", "Evaluate whether project memory, reasoning bank, or memento-style context improves or contaminates the answer."],
    ["Hyperagent workflow audit", "Use the safest available hyperagent or governed-improvement path and review whether it produced a bounded useful improvement."],
    ["Compute and ensemble health audit", "Verify donated compute health, model routing, and any ensemble/MoA health evidence before relying on synthesis."],
  ];
  const tasks = [];
  for (let i = 0; i < total; i += 1) {
    const [title, description] = taskTypes[i % taskTypes.length];
    tasks.push({
      title: `[RU-${String(i + 1).padStart(2, "0")}] ${title}`,
      description,
      skill_name: i % 5 === 0 ? "analyze-interview" : "",
      priority: i % 9 === 0 ? "high" : "medium",
      labels: ["real-user-benchmark", i % 7 === 0 ? "needs-citations" : "synthesis"],
      shouldReviseFirst: i % 8 === 0,
      acceptance: [
        "Names at least two source documents when evidence is synthesized.",
        "Distinguishes evidence, interpretation, and recommendation.",
        "States confidence or uncertainty.",
        "Avoids medical advice and private patient disclosure.",
      ],
    });
  }
  return tasks;
}

export function reviewerAssessment(task, agentNotes) {
  const notes = String(agentNotes || "");
  const issues = [];
  if (notes.length < 80) issues.push("output is too brief");
  if (!/source|interview|survey|usability|ticket|diary/i.test(notes)) issues.push("missing source references");
  if (!/confidence|uncertain|evidence|because/i.test(notes)) issues.push("missing confidence or evidence reasoning");
  if (/medical advice|diagnose|treatment plan/i.test(notes)) issues.push("unsafe medical inference");
  const approved = issues.length === 0;
  return {
    approved,
    issues,
    score: Math.max(0, 1 - issues.length * 0.25),
    revisionInstruction: issues.length
      ? `Please revise ${task.title}: ${issues.join("; ")}. Add source names, separate evidence from interpretation, and state confidence.`
      : `Approved: output is specific, grounded, and reviewable for ${task.title}.`,
  };
}
