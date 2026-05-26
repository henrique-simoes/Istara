import { existsSync, mkdirSync, rmSync, writeFileSync } from "fs";
import { basename, join } from "path";
import { spawnSync } from "child_process";
import {
  SHARED_DOCUMENT_CORPUS_MINIMUM_SOURCES,
  canonicalCorpusSummary,
  materializeSharedDocumentCorpus,
} from "../../document_corpus/shared-corpus.mjs";

export const PROJECT_CONTEXT = {
  name: "CareNav Renewal",
  company: "Northstar Health",
  industry: "multi-site outpatient health operations",
  audience: "care coordinators, patients, family caregivers, nurse managers, clinic administrators, operations analysts, accessibility reviewers, and product stakeholders",
  product: "CareNav, a patient-care coordination workspace for appointment preparation, readiness evidence, caregiver collaboration, multilingual reminders, staff handoff, and governed automation",
  stage: "research-heavy renewal after a failed multi-clinic pilot and before a high-risk regional relaunch decision",
  companyContext: [
    "Northstar Health operates 43 outpatient clinics across community health, cardiology, oncology, pediatrics, fertility, and post-operative care. The organization introduced CareNav to reduce missed appointment-preparation tasks, same-day cancellations, staff phone burden, and unsafe manual workarounds across portal messages, SMS reminders, EHR work queues, caregiver calls, and paper notes.",
    "The failed pilot produced mixed evidence. Operations leaders saw early reductions in missed prep for some clinics, but coordinators still rebuilt source trails by hand, caregivers called because permission states were unclear, multilingual reminders diverged from English source copy, and patients could not tell which tasks were required before the visit. Northstar now needs a governed relaunch decision that respects clinical safety, privacy, multilingual accessibility, staff workload, and the Research Spine.",
    "The benchmark project should feel like a real senior UX research engagement. A researcher configures business context, risk boundaries, source inventory, stakeholder decision pressure, and explicit report gates. Istara must not treat raw model output, memory, telemetry, RAG snippets, GraphRAG synthesis, or generated interface ideas as accepted evidence unless they pass source-grounded extraction/coding, reliability or reconciliation, task review, and Done/report gates.",
  ].join("\n\n"),
  projectContext: [
    "Research objective: decide what CareNav should redesign first for a regional relaunch, what should remain human-reviewed, and what evidence is strong enough to support leadership recommendations. The core problem is not simply reminders; it is whether appointment readiness can be made trustworthy across patients, caregivers, coordinators, nurse managers, and administrators without turning automation into a black box.",
    "Source inventory: the canonical program contains 174 upload-compatible synthetic sources spanning one-hour interview transcripts, participant profiles, diary studies, moderated usability sessions, surveys, NPS/SUS/UMUX exports, card sorting, tree testing, journey maps, field notes, support tickets, analytics exports, A/B tests, competitor analysis, heuristic evaluation, accessibility review, Laws of UX audit, product briefs, stakeholder memos, research plans, discussion guides, consent/privacy notes, multilingual material, malformed edge-case files, and report-readiness material. The evidence intentionally includes contradictions, stale metrics, low-confidence statements, and multilingual ambiguity.",
    "Research process requirement: every source should become stable evidence units before trusted atomic artifacts exist. Independent model coders should extract candidate atomic facts and open codes from source spans, preserve quote/span grounding, compare claim and code agreement, compute reliability or companion grounding checks, reconcile disagreement through debate/adversarial/human review, and only then promote accepted atoms into facts, insights, recommendations, In Review tasks, Done tasks, and Reports.",
    "Decision horizon: the executive team wants a relaunch recommendation in two weeks. The research team must identify the smallest high-confidence design slice to prototype, document unresolved risks, and avoid overclaiming. The benchmark should test whether Istara can sustain this complexity while preserving route evidence, project-scoped compute donation, reviewer state, and report gating.",
  ].join("\n\n"),
  successMetrics: [
    "Evidence-chain completeness from raw source to report paragraph.",
    "Ability to separate patient, caregiver, staff, admin, and operations evidence.",
    "Correct handling of contradictory evidence and low-agreement coding.",
    "Usefulness of task review loops and human Done approval.",
    "Route evidence for multi-model donated compute during coding, chat, and synthesis.",
    "Quality of report exclusions: what Istara refuses to report because evidence is provisional, low-consensus, or taskless.",
  ],
  guardrails: [
    "Do not infer medical advice, diagnosis, treatment priority, clinical eligibility, insurance coverage, or medication guidance.",
    "Treat every participant story as synthetic PHI-like material; do not expose names, phone numbers, addresses, or unnecessary identity details in report outputs.",
    "Separate staff workflow evidence from patient, caregiver, administrator, and operations analyst evidence until a synthesis explicitly compares them.",
    "Flag contradictions, stale evidence, sampling gaps, language-specific wording risks, and automation-trust risks instead of smoothing them into one confident theme.",
    "Do not let raw model output, RAG retrieval, GraphRAG synthesis, ReasoningBank memory, Memento skill memory, telemetry, or self-improvement proposals become report evidence by themselves.",
    "Recommendations must cite source ids, exact quotes or spans where possible, codebook/reliability status, reconciliation status, reviewer state, and human-approved Done task links before they become reportable.",
    "When only one model is available, mark the path lower assurance; when two or three distinct healthy project-authorized models are available, use the correct two-coder or full multi-model validation path.",
    "Credential-free integration probes for AURA, surveys, Telegram, Figma, Stitch, and forms should classify setup blockers honestly; do not invent third-party data or claim successful integration without evidence.",
  ],
  researchQuestions: [
    "Where does appointment-preparation coordination break down across portal tasks, SMS reminders, caregiver calls, staff dashboards, EHR work queues, and manual paper workarounds?",
    "Which reminders feel supportive, timely, and privacy-aware versus repetitive, nagging, or unsafe, and how does that differ by role, language, clinic type, and appointment journey?",
    "What evidence does staff need before they trust an automated readiness status, override recommendation, escalation, or task-priority label?",
    "How should caregiver involvement be represented so patients understand consent boundaries, caregivers know what they can safely do, and staff can explain the source of each permission state?",
    "Which contradictions require reconciliation before leadership can act, especially when survey metrics, support tickets, interviews, usability observations, and analytics point in different directions?",
    "Which atomic facts/nuggets can become accepted after source-grounded coding and reliability checks, which remain provisional, and which must be rejected as unsupported or over-interpreted?",
    "What should the first relaunch prototype include, what should remain explicitly human-reviewed, and what should be excluded from Reports until more evidence is gathered?",
  ],
};

const participants = [
  ["P01", "Marta", "care coordinator", "rural clinic", "Portuguese bilingual"],
  ["P02", "Leo", "patient", "diabetes follow-up", "mobile-first"],
  ["P03", "Asha", "caregiver", "elder care", "limited portal access"],
  ["P04", "Nina", "nurse manager", "urban clinic", "dashboard owner"],
  ["P05", "Owen", "patient", "post-op prep", "low confidence"],
  ["P06", "Ravi", "care coordinator", "specialty clinic", "high caseload"],
  ["P07", "Elena", "caregiver", "Spanish bilingual", "shared device"],
  ["P08", "Sam", "clinic admin", "pilot sponsor", "data governance"],
  ["P09", "Priya", "patient", "fertility consult", "privacy sensitive"],
  ["P10", "Jon", "care coordinator", "pediatrics", "paper workaround"],
  ["P11", "Beatriz", "patient", "cardiology", "Portuguese notes"],
  ["P12", "Camila", "caregiver", "oncology", "high anxiety"],
  ["P13", "Hannah", "care coordinator", "community health", "SMS-heavy workflow"],
  ["P14", "Andre", "patient", "Spanish follow-up", "missed labs"],
  ["P15", "Monique", "nurse", "handoff lead", "EHR constraints"],
  ["P16", "Iris", "patient", "first-time portal user", "accessibility needs"],
  ["P17", "Diego", "caregiver", "multi-household", "permissions confusion"],
  ["P18", "Kai", "operations analyst", "analytics owner", "source of metrics"],
];

const painPoints = [
  "patients cannot tell which tasks are required before the appointment",
  "staff duplicate reminders in SMS, portal messages, and sticky notes",
  "caregivers receive partial information and then call the clinic",
  "the dashboard hides stale tasks until the day before a visit",
  "forms look complete even when lab attachments are missing",
  "Spanish and Portuguese copy is inconsistent across reminders",
  "staff do not trust automation when no source trail is shown",
  "patients miss reminders sent during working hours",
];

const opportunities = [
  "show a preparation timeline with required, optional, and blocked steps",
  "surface the source and freshness of each task",
  "give coordinators a one-click reason for overriding automation",
  "create a caregiver-safe view with explicit permission labels",
  "collapse duplicate reminders into a single communication history",
  "add confidence labels when evidence is incomplete",
  "summarize appointment readiness without medical interpretation",
  "let staff filter by next patient action instead of visit date only",
];

function writeFile(root, relPath, content) {
  const path = join(root, relPath);
  mkdirSync(join(path, ".."), { recursive: true });
  writeFileSync(path, content);
  return {
    path,
    file_name: basename(path),
    relative_path: relPath,
    bytes: Buffer.byteLength(content),
  };
}

function interviewTranscript(index, participant) {
  const [id, name, role, segment, note] = participant;
  const pain = painPoints[index % painPoints.length];
  const secondPain = painPoints[(index + 3) % painPoints.length];
  const opportunity = opportunities[index % opportunities.length];
  return [
    `# Interview ${id}: ${role} - ${segment}`,
    "",
    `Participant: ${name}`,
    `Context: ${note}`,
    `Date: 2026-04-${String((index % 24) + 1).padStart(2, "0")}`,
    "Moderator: Maya Rodrigues",
    "",
    "## Transcript",
    `[00:00] Maya: Thanks for joining. I am trying to understand how appointment preparation works from your perspective.`,
    `[00:31] ${name}: The biggest thing is that ${pain}.`,
    `[01:24] Maya: Can you walk me through the last time that happened?`,
    `[02:02] ${name}: We had a visit where the portal said everything was ready, but ${secondPain}. I only noticed because someone called.`,
    `[03:18] Maya: What did you do next?`,
    `[03:51] ${name}: I made a note outside the system. That is risky, but it is faster than searching three places.`,
    `[05:09] Maya: What would make the system trustworthy?`,
    `[05:42] ${name}: I need to see why it thinks a task is ready. A status alone is not enough.`,
    `[07:00] Maya: If you could change one thing, what would it be?`,
    `[07:33] ${name}: ${opportunity}. Then I would not need to keep my own tracker.`,
    "",
    "## Researcher memo",
    `Evidence strength: ${index % 4 === 0 ? "high" : "medium"}.`,
    `Potential contradiction: ${index % 3 === 0 ? "participant says reminders are too frequent, but analytics show low open rates" : "none noted"}.`,
  ].join("\n");
}

function usabilityReport(index) {
  const scenario = [
    "Prepare for a cardiology follow-up",
    "Invite a caregiver to review tasks",
    "Resolve a missing lab attachment",
    "Override an automated reminder",
    "Find patients blocked by unanswered forms",
    "Explain appointment readiness to a nurse",
  ][index % 6];
  const completion = 58 + ((index * 7) % 35);
  return [
    `# Usability Test U${String(index + 1).padStart(2, "0")}`,
    "",
    `Scenario: ${scenario}`,
    `Prototype: CareNav v${index % 2 === 0 ? "A" : "B"}`,
    `Participants: ${6 + (index % 3)}`,
    "",
    "| Task | Completion | Median Time | Notes |",
    "| --- | ---: | ---: | --- |",
    `| Locate blocked tasks | ${completion}% | ${90 + index * 8}s | Users scanned visit dates before task status |`,
    `| Identify missing evidence | ${completion - 11}% | ${120 + index * 11}s | Source trail label was missed by 4 participants |`,
    `| Send caregiver-safe update | ${completion - 18}% | ${150 + index * 9}s | Permission wording caused hesitation |`,
    "",
    "## Observed friction",
    `- ${painPoints[index % painPoints.length]}.`,
    `- ${painPoints[(index + 5) % painPoints.length]}.`,
    "- Users expected a plain-language readiness reason next to the status.",
    "",
    "## Moderator recommendations",
    `- ${opportunities[index % opportunities.length]}.`,
    "- Test permission copy with caregivers before expanding the flow.",
  ].join("\n");
}

function diaryStudy() {
  const lines = ["participant_id,day,role,event,emotion,quote"];
  for (let p = 1; p <= 10; p += 1) {
    for (let day = 1; day <= 5; day += 1) {
      const pain = painPoints[(p + day) % painPoints.length];
      const emotion = ["confident", "confused", "rushed", "relieved", "skeptical"][(p + day) % 5];
      lines.push(`D${String(p).padStart(2, "0")},${day},${participants[p % participants.length][2]},appointment prep,${emotion},"Today ${pain}; I wrote a workaround note."`);
    }
  }
  return lines.join("\n");
}

function surveyCsv() {
  const headers = [
    "respondent_id",
    "role",
    "language",
    "clinic_type",
    "readiness_trust",
    "reminder_clarity",
    "caregiver_confidence",
    "time_saved_minutes",
    "nps",
    "open_feedback",
  ];
  const rows = [headers.join(",")];
  const roles = ["patient", "caregiver", "care coordinator", "nurse manager", "clinic admin"];
  const languages = ["en", "en", "es", "pt-BR"];
  for (let i = 1; i <= 320; i += 1) {
    const role = roles[i % roles.length];
    const trust = 2 + (i % 4);
    const clarity = 1 + ((i * 3) % 5);
    const caregiver = 1 + ((i * 5) % 5);
    const saved = (i * 7) % 45;
    const nps = (i * 9) % 11;
    const feedback = `${painPoints[i % painPoints.length]} but ${opportunities[(i + 2) % opportunities.length]}`;
    rows.push([
      `R${String(i).padStart(3, "0")}`,
      role,
      languages[i % languages.length],
      i % 3 === 0 ? "community" : "specialty",
      trust,
      clarity,
      caregiver,
      saved,
      nps,
      `"${feedback}"`,
    ].join(","));
  }
  return rows.join("\n");
}

function analyticsCsv() {
  const rows = ["week,portal_task_open_rate,sms_click_rate,missed_prep_rate,staff_override_rate,avg_minutes_per_case"];
  for (let week = 1; week <= 16; week += 1) {
    rows.push([
      `2026-W${String(week).padStart(2, "0")}`,
      (0.41 + week * 0.01).toFixed(2),
      (0.28 + (week % 5) * 0.03).toFixed(2),
      (0.38 - week * 0.008).toFixed(2),
      (0.12 + (week % 4) * 0.02).toFixed(2),
      18 + (week % 6),
    ].join(","));
  }
  return rows.join("\n");
}

function supportTicketsJsonl() {
  const lines = [];
  for (let i = 1; i <= 160; i += 1) {
    lines.push(JSON.stringify({
      ticket_id: `T-${String(i).padStart(4, "0")}`,
      channel: ["phone", "portal", "sms", "front desk"][i % 4],
      role: ["patient", "caregiver", "care coordinator"][i % 3],
      severity: ["low", "medium", "high"][i % 3],
      summary: painPoints[i % painPoints.length],
      resolution: i % 5 === 0 ? "manual follow-up required" : "answered with workaround",
      tags: ["prep", "reminder", i % 2 === 0 ? "caregiver" : "staff"],
    }));
  }
  return lines.join("\n");
}

function competitorNotes() {
  return [
    "# Competitor Review Notes",
    "",
    "| Competitor | Strong Pattern | Weak Pattern | Implication |",
    "| --- | --- | --- | --- |",
    "| WellPath Tasks | Clear readiness timeline | No caregiver permission labels | Timeline is valuable, but privacy language matters |",
    "| ClinicFlow | Staff override reason is captured | Patient view is buried | Trust grows when staff decisions are visible |",
    "| RemindRx | SMS reminders are concise | No source trail for tasks | Concision helps, missing evidence hurts adoption |",
    "| CareBridge | Caregiver roles are explicit | Setup is long | Permission framing should be progressive |",
  ].join("\n");
}

function multilingualExamples() {
  return [
    "# Multilingual Reminder Examples",
    "",
    "## Portuguese",
    "Paciente: Nao entendi se o exame de sangue e obrigatorio antes da consulta. A mensagem parecia opcional.",
    "Cuidadora: Recebi o lembrete, mas nao tenho permissao para ver o anexo.",
    "",
    "## Spanish",
    "Paciente: La aplicacion dijo que todo estaba listo, pero la clinica llamo por un formulario pendiente.",
    "Cuidador: Necesito saber que puedo hacer sin ver informacion privada.",
  ].join("\n");
}

function malformedFile() {
  return [
    "participant_id,role,quote",
    "M01,patient,\"The reminder said ready",
    "M02,caregiver,missing closing quote and extra field,unexpected",
    "\u0000\u0001bad-bytes-represented-as-text",
    "M03,,blank role should be handled",
  ].join("\n");
}

function writeMinimalPptx(root, relPath) {
  const temp = join(root, ".pptx-tmp");
  rmSync(temp, { recursive: true, force: true });
  mkdirSync(join(temp, "_rels"), { recursive: true });
  mkdirSync(join(temp, "ppt", "_rels"), { recursive: true });
  mkdirSync(join(temp, "ppt", "slides", "_rels"), { recursive: true });
  mkdirSync(join(temp, "ppt", "slides"), { recursive: true });
  writeFileSync(join(temp, "[Content_Types].xml"), `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
<Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
</Types>`);
  writeFileSync(join(temp, "_rels", ".rels"), `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>`);
  writeFileSync(join(temp, "ppt", "presentation.xml"), `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><p:sldIdLst><p:sldId id="256" r:id="rId1"/></p:sldIdLst><p:sldSz cx="12192000" cy="6858000" type="screen16x9"/></p:presentation>`);
  writeFileSync(join(temp, "ppt", "_rels", "presentation.xml.rels"), `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/>
</Relationships>`);
  writeFileSync(join(temp, "ppt", "slides", "slide1.xml"), `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/><p:sp><p:nvSpPr><p:cNvPr id="2" name="Title"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:t>CareNav Renewal Research Readout</a:t></a:r></a:p><a:p><a:r><a:t>Key risk: readiness status lacks source trust.</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sld>`);
  const outPath = join(root, relPath);
  mkdirSync(join(outPath, ".."), { recursive: true });
  const result = spawnSync("zip", ["-qr", outPath, "."], { cwd: temp, encoding: "utf8" });
  rmSync(temp, { recursive: true, force: true });
  if (result.status !== 0 || !existsSync(outPath)) {
    return writeFile(root, relPath.replace(/\.pptx$/, ".pptx.txt"), "PPTX fallback: CareNav Renewal Research Readout\nKey risk: readiness status lacks source trust.\n");
  }
  return {
    path: outPath,
    file_name: basename(outPath),
    relative_path: relPath,
    bytes: 0,
    generated_with: "minimal-openxml-zip",
  };
}

export function generateCorpus({ outputDir, logger }) {
  mkdirSync(outputDir, { recursive: true });
  const manifest = [];
  const sharedCorpus = materializeSharedDocumentCorpus({
    outputDir,
    existingManifest: manifest,
    minimumSources: SHARED_DOCUMENT_CORPUS_MINIMUM_SOURCES,
    slice: "full-end-to-end",
    canonicalOnly: true,
    logger,
  });
  manifest.push(...sharedCorpus.manifest);
  const canonicalSummary = canonicalCorpusSummary();

  const summary = {
    project: PROJECT_CONTEXT,
    generated_at: new Date().toISOString(),
    canonical_corpus: canonicalSummary,
    shared_corpus: {
      minimum_sources: SHARED_DOCUMENT_CORPUS_MINIMUM_SOURCES,
      slice: sharedCorpus.slice,
      canonical_count: sharedCorpus.canonical_count,
      fixture_count: sharedCorpus.fixture_count,
      generated_count: sharedCorpus.generated_count,
    },
    document_count: manifest.length,
    total_bytes: manifest.reduce((sum, item) => sum + (item.bytes || 0), 0),
    manifest,
  };
  writeFileSync(join(outputDir, "corpus-manifest.json"), JSON.stringify(summary, null, 2));
  logger?.action("corpus.generated", {
    document_count: summary.document_count,
    total_bytes: summary.total_bytes,
    output_dir: outputDir,
  });
  return summary;
}
