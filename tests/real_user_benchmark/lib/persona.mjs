export const RESEARCHER_PERSONAS = [
  {
    key: "admin",
    displayName: "Maya Rodrigues",
    role: "global-admin-project-lead",
    focus: "project setup, access, governance, and final evidence quality",
  },
  {
    key: "researcher-1",
    displayName: "Ana Lima",
    role: "researcher",
    focus: "interviews, caregiver trust, multilingual evidence, and document work",
  },
  {
    key: "researcher-2",
    displayName: "Theo Mendes",
    role: "researcher",
    focus: "task review, source grounding, survey sanity checks, and findings readiness",
  },
];

const PROGRAM_CONTEXT = [
  "Northstar Health is preparing a high-risk regional relaunch of CareNav, a patient-care coordination workspace that tries to make appointment-preparation tasks trustworthy across portal messages, SMS reminders, caregiver permissions, staff dashboards, EHR handoffs, analytics, and human review. The previous pilot failed unevenly: some clinics saw fewer missed prep tasks, but coordinators rebuilt evidence trails manually, caregivers called because permissions were unclear, multilingual reminders diverged from English source copy, and patients could not tell which steps were required before an appointment. Treat this benchmark as a senior mixed-methods research engagement, not a toy demo.",
  "The canonical source archive contains 174 synthetic but realistic sources: long interview transcripts, participant profiles, diary studies, usability studies, surveys, NPS/SUS/UMUX exports, card sorting, tree testing, journey maps, field notes, support tickets, analytics exports, A/B tests, competitor benchmarks, heuristic and accessibility audits, Laws of UX audits, stakeholder memos, research plans, discussion guides, consent notes, multilingual material, malformed edge-case exports, and report-readiness documents. The material intentionally contains contradictions, stale metrics, low-confidence observations, language-specific risk, and evidence that should remain provisional until reconciled.",
  "Use Istara according to the Research Spine. Segment raw sources into stable evidence units. Treat model outputs as candidate atomic facts and candidate codes until independent multi-model extraction/coding, quote/span comparison, reliability or grounding checks, and reconciliation make them accepted. Do not let RAG, GraphRAG, Prompt-RAG, LLMLingua, ReasoningBank, Memento Skills, Meta-Hyperagent, Autoresearch, telemetry, or a skill result become report evidence by itself. Reports must use accepted/reconciled evidence attached to human-approved Done tasks.",
].join("\n\n");

const STANDARD_DELIVERABLES = [
  "Name the exact source types or source ids you expect to use, and say where retrieval or coding should begin.",
  "Separate evidence, interpretation, recommendation, confidence, contradiction, and next action.",
  "Call out which claims are candidate/provisional and which could become accepted only after reliability or reconciliation.",
  "Preserve patient, caregiver, staff, admin, language, clinic, and journey distinctions.",
  "Flag any missing data, role permission issue, integration credential blocker, or unsafe medical inference.",
  "Explain what should become an In Review task and what would be required before the task can move to Done.",
];

function detailedChatPrompt(base, index, intent) {
  const focusAreas = [
    "evidence-unit extraction and open coding",
    "multi-model reliability and disagreement reconciliation",
    "caregiver permission language and multilingual risk",
    "staff trust in readiness automation and source trails",
    "patient appointment-prep confusion and reminder fatigue",
    "survey, analytics, and support-ticket triangulation",
    "usability, accessibility, and interface decision quality",
    "task review, Done approval, and report gating",
    "ReasoningBank, Memento Skills, Meta-Hyperagent, Autoresearch, and governed self-improvement",
    "donated compute, route evidence, and ensemble health",
  ];
  const focus = focusAreas[index % focusAreas.length];
  return [
    `Researcher request ${index + 1} (${intent}; focus: ${focus}).`,
    "",
    base,
    "",
    PROGRAM_CONTEXT,
    "",
    "Work the way a real senior UX researcher would. Assume I am under stakeholder pressure to produce a launch recommendation, but I do not want an easy narrative. I want you to slow down where the evidence is messy, use the canonical corpus rather than generic UX advice, and keep every downstream artifact tied to source-grounded evidence. If you need to use search, RAG, GraphRAG, a skill, a tool call, an agent workflow, a task, or a review queue, explain why that surface is appropriate and what evidence it should preserve. If a feature is unavailable because credentials are missing, classify the blocker rather than pretending it worked.",
    "",
    "Please respond with a research-grade structure. Start with the specific evidence path you would use. Then give the synthesis or requested action. Then list contradictions, confidence, and what should remain provisional. When you propose a task, finding, insight, recommendation, interface direction, or report paragraph, explicitly state how it would travel through evidence units, candidate atoms/codes, reliability or reconciliation, human review, Done approval, and report gating. Do not collapse staff, patient, caregiver, language, or clinic evidence unless you explain the comparison basis.",
    "",
    "Minimum deliverables for this turn:",
    ...STANDARD_DELIVERABLES.map((item) => `- ${item}`),
    "",
    "If you cannot complete a requested action, say exactly what blocked it and produce the most useful next research task instead. Avoid medical advice and avoid exposing participant identity. Prefer source-cited, uncertainty-aware output over polished but unsupported synthesis.",
  ].join("\n");
}

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
    content: detailedChatPrompt(content, index, index < seedTurns.length ? "scenario-steering" : "natural-follow-up"),
    intent: index < seedTurns.length ? "scenario-steering" : "natural-follow-up",
  }));
}

export function buildCollaborativeChatTurns({ total = 108, actors = RESEARCHER_PERSONAS.slice(1) } = {}) {
  const activeActors = actors.length ? actors : RESEARCHER_PERSONAS.slice(1);
  return buildChatTurns({ total }).map((turn, index) => {
    const actor = activeActors[index % activeActors.length] || RESEARCHER_PERSONAS[0];
    return {
      ...turn,
      speaker: actor.displayName,
      actor_key: actor.key,
      actor_role: actor.role,
      actor_focus: actor.focus,
      content: index < activeActors.length
        ? `${turn.content}\n\nI am ${actor.displayName}; focus this answer on ${actor.focus}.`
        : turn.content,
    };
  });
}

export function buildTaskPlan({ total = 60, actors = RESEARCHER_PERSONAS.slice(1) } = {}) {
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
  const activeActors = actors.length ? actors : RESEARCHER_PERSONAS.slice(1);
  for (let i = 0; i < total; i += 1) {
    const [title, description] = taskTypes[i % taskTypes.length];
    const creator = activeActors[i % activeActors.length] || RESEARCHER_PERSONAS[0];
    const reviewer = activeActors.length > 1
      ? activeActors[(i + 1) % activeActors.length]
      : RESEARCHER_PERSONAS[0];
    tasks.push({
      title: `[RU-${String(i + 1).padStart(2, "0")}] ${title}`,
      description: detailedTaskDescription({
        title,
        description,
        index: i,
      }),
      skill_name: i % 5 === 0 ? "analyze-interview" : "",
      priority: i % 9 === 0 ? "high" : "medium",
      labels: ["real-user-benchmark", i % 7 === 0 ? "needs-citations" : "synthesis"],
      creator_key: creator.key,
      creator_name: creator.displayName,
      reviewer_key: reviewer.key,
      reviewer_name: reviewer.displayName,
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

function detailedTaskDescription({ title, description, index }) {
  const methodMixes = [
    "interviews, diary studies, field notes, and support tickets",
    "surveys, NPS/SUS/UMUX rows, analytics exports, and open verbatims",
    "usability sessions, accessibility audits, heuristic notes, and interface artifacts",
    "stakeholder memos, competitor benchmarks, A/B tests, and report-readiness material",
    "AURA-style interview planning, integration setup evidence, and credential-free blocker logs",
  ];
  const methodMix = methodMixes[index % methodMixes.length];
  return [
    description,
    "",
    PROGRAM_CONTEXT,
    "",
    `Task objective: perform "${title}" as if you are preparing evidence for a real human research review, using ${methodMix}. The goal is not to produce a pretty summary. The goal is to create reviewable research work that can survive the Research Spine. Start from raw source material, name the likely source ids or file types, identify stable evidence units, and describe how candidate atomic facts and open codes should be generated independently by available project-authorized models. Where the evidence is contradictory or low-confidence, keep it provisional and route it to reconciliation instead of turning it into a finding.`,
    "",
    "Required analysis depth: distinguish staff, patient, caregiver, administrator, operations analyst, language, clinic type, and journey context. Compare at least two evidence types, and say whether they agree, conflict, or answer different questions. Look for source freshness, owner, permission state, reminder timing, readiness confidence, manual workaround, accessibility friction, and automation-trust signals. If a skill, RAG search, GraphRAG synthesis, ReasoningBank memory, Memento Skill, Meta-Hyperagent proposal, Autoresearch result, Prompt-RAG context, or compression path helps, use it only as process support and state why it cannot bypass evidence validation.",
    "",
    "Review output requirements: produce notes that a reviewer can approve or send back. Include source references, candidate evidence units, candidate codes, confidence, contradictions, risk classification, and next action. Separate evidence from interpretation and recommendations. Identify what would become an accepted atom only after reliability or reconciliation, what should become an In Review task, what would be required for Done approval, and which report paragraph or interface decision would remain blocked until the evidence is accepted. Do not infer medical advice, do not expose participant identity, and do not claim integration success without credentialed or mock-path evidence.",
    "",
    "Acceptance standard: this task should be rejected if it has fewer than two concrete source references, merges incompatible roles without explanation, summarizes raw material as reportable evidence, treats telemetry or memory as research evidence, ignores low-consensus contradictions, lacks confidence language, or proposes a report recommendation before task approval. It should be approved only if it is source-grounded, uncertainty-aware, role-aware, and explicit about the path from source evidence to accepted research artifact.",
  ].join("\n");
}

export function buildInterviewProcessPlan() {
  return {
    title: "[RU-INTERVIEW] Appointment-prep adaptive interview process",
    description: detailedTaskDescription({
      title: "Appointment-prep adaptive interview process",
      description: "Use uploaded interview transcripts and local project evidence to prepare adaptive follow-up questions, analyze participant responses, and identify what a credential-free run can and cannot prove.",
      index: 0,
    }),
    skill_name: "analyze-interview",
    priority: "high",
    labels: ["real-user-benchmark", "interviews", "agentic-workflow"],
    creator_key: "researcher-1",
    creator_name: "Ana Lima",
    reviewer_key: "researcher-2",
    reviewer_name: "Theo Mendes",
    shouldReviseFirst: true,
    external_credentials_required: ["Telegram bot token", "AURA participant channel credentials"],
    future_improvement: "Add a credential-free participant conversation simulator so AURA deployments can be tested through real inbound conversations without external tokens.",
    acceptance: [
      "Names at least two interview or transcript sources.",
      "Separates interview-guide questions from transcript analysis.",
      "States which external participant-channel steps were skipped because credentials are not available.",
      "Produces a reviewable next-pass research task.",
    ],
  };
}

export function reviewerAssessment(task, agentNotes) {
  const notes = String(agentNotes || "");
  const issues = [];
  if (notes.length < 80) issues.push("output is too brief");
  if (!/source|interview|survey|usability|ticket|diary/i.test(notes)) issues.push("missing source references");
  if (!/confidence|uncertain|evidence|because/i.test(notes)) issues.push("missing confidence or evidence reasoning");
  if (/medical advice|diagnose|treatment plan/i.test(notes)) issues.push("unsafe medical inference");
  if (/\b(blocked|awaiting data|awaiting input|input data missing|required source documents|missing source material|source material.*missing|raw .*data .*not provided|cannot (?:complete|proceed|provide|perform|execute)|could not be (?:found|located)|document not found|no documents found)\b/i.test(notes)) {
    issues.push("output says the work is blocked or required sources are missing");
  }
  if (/\b(confidence (?:level:?\s*)?low|confidence:\s*low|confidence in task completion:\s*low)\b/i.test(notes)) {
    issues.push("output is low confidence");
  }
  if (/\bsynthetic\b/i.test(notes) && /source|interview|survey|usability|ticket|diary|transcript/i.test(`${task.title} ${task.description || ""}`)) {
    issues.push("source-backed task relies on synthetic evidence");
  }
  const concreteSourceMentions = notes.match(/\b(?:P\d{2}[-\w]*\.md|[\w-]+\.csv|Transcript\s*\([^)]+\)|Source:\s*[^)\]\n]+|`[^`]+\.(?:md|csv|json)`)\b/gi) || [];
  if (concreteSourceMentions.length < 2 && /source|interview|survey|usability|ticket|diary|transcript/i.test(`${task.title} ${task.description || ""}`)) {
    issues.push("names fewer than two concrete source artifacts");
  }
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
