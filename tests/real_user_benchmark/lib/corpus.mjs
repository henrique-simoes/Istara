import { existsSync, mkdirSync, rmSync, writeFileSync } from "fs";
import { basename, join } from "path";
import { spawnSync } from "child_process";

export const PROJECT_CONTEXT = {
  name: "CareNav Renewal",
  company: "Northstar Health",
  audience: "care coordinators, patients, family caregivers, and clinic administrators",
  product: "a patient-care coordination workspace for appointment prep, reminders, and task follow-up",
  stage: "mid-fidelity redesign after a failed pilot",
  guardrails: [
    "Do not infer medical advice.",
    "Treat patient stories as synthetic PHI-like data and avoid exposing names in reports.",
    "Separate staff workflow evidence from patient/caregiver evidence.",
    "Flag contradictions and missing sampling context.",
    "Prefer source-cited recommendations over generic UX advice.",
  ],
  researchQuestions: [
    "Where does appointment-prep coordination break down?",
    "Which reminders feel supportive versus nagging?",
    "What does staff need to trust automation?",
    "How should caregiver involvement be represented without confusing consent?",
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

  manifest.push(writeFile(outputDir, "00-project-context.md", [
    `# ${PROJECT_CONTEXT.name}`,
    "",
    `Company: ${PROJECT_CONTEXT.company}`,
    `Audience: ${PROJECT_CONTEXT.audience}`,
    `Product: ${PROJECT_CONTEXT.product}`,
    `Stage: ${PROJECT_CONTEXT.stage}`,
    "",
    "## Guardrails",
    ...PROJECT_CONTEXT.guardrails.map((item) => `- ${item}`),
    "",
    "## Research Questions",
    ...PROJECT_CONTEXT.researchQuestions.map((item) => `- ${item}`),
  ].join("\n")));

  participants.forEach((participant, index) => {
    manifest.push(writeFile(outputDir, `interviews/${participant[0]}-${participant[2].replace(/\s+/g, "-")}.md`, interviewTranscript(index, participant)));
  });

  for (let i = 0; i < 6; i += 1) {
    manifest.push(writeFile(outputDir, `usability/usability-test-${String(i + 1).padStart(2, "0")}.md`, usabilityReport(i)));
  }

  manifest.push(writeFile(outputDir, "surveys/carenav-survey-180.csv", surveyCsv()));
  manifest.push(writeFile(outputDir, "diary/diary-study-week.csv", diaryStudy()));
  manifest.push(writeFile(outputDir, "analytics/pilot-analytics.csv", analyticsCsv()));
  manifest.push(writeFile(outputDir, "support/support-tickets.jsonl", supportTicketsJsonl()));
  manifest.push(writeFile(outputDir, "competitive/competitor-notes.md", competitorNotes()));
  manifest.push(writeFile(outputDir, "design/design-critique-notes.md", [
    "# Design Critique Notes",
    "",
    "- Readiness badge looks definitive even when evidence is stale.",
    "- Staff need a visible override reason before trusting automated reminders.",
    "- Caregiver panel uses the same visual hierarchy as patient tasks, causing role confusion.",
    "- The timeline prototype scored better than the checklist prototype in scan tests.",
  ].join("\n")));
  manifest.push(writeFile(outputDir, "field-notes/clinic-shadowing.md", [
    "# Clinic Shadowing Field Notes",
    "",
    "Morning huddle: three coordinators compared portal tasks with handwritten notes.",
    "One nurse said the team trusts the sticky note because it has a person's initials.",
    "A caregiver called twice about a lab form that was complete in one system but missing in another.",
    "Staff asked for a readiness queue grouped by next action, not appointment date.",
  ].join("\n")));
  for (let i = 1; i <= 8; i += 1) {
    manifest.push(writeFile(outputDir, `stakeholder-memos/stakeholder-memo-${String(i).padStart(2, "0")}.md`, [
      `# Stakeholder Memo ${i}`,
      "",
      `Owner: ${["Operations", "Clinical Safety", "Patient Experience", "Compliance"][i % 4]}`,
      `Decision pressure: ${painPoints[(i + 2) % painPoints.length]}.`,
      "",
      "## Position",
      `The stakeholder believes the redesign should prioritize ${opportunities[(i + 1) % opportunities.length]}.`,
      "",
      "## Tension",
      `This may conflict with ${opportunities[(i + 4) % opportunities.length]} because teams have different views of readiness ownership.`,
      "",
      "## Evidence requested",
      "- More separation between patient, caregiver, and staff workflows.",
      "- Stronger proof that source trails reduce support calls.",
      "- A clear privacy review before caregiver-facing launch.",
    ].join("\n")));
  }
  for (let i = 1; i <= 12; i += 1) {
    manifest.push(writeFile(outputDir, `experiments/concept-test-${String(i).padStart(2, "0")}.md`, [
      `# Concept Test ${i}`,
      "",
      `Concept: ${["Timeline", "Checklist", "Readiness Score", "Caregiver Card"][i % 4]}`,
      `Stimulus: mid-fidelity screen set ${String.fromCharCode(64 + ((i % 4) + 1))}`,
      "",
      "## What worked",
      `- ${opportunities[i % opportunities.length]}.`,
      "- Participants understood required versus optional labels faster than status-only labels.",
      "",
      "## What failed",
      `- ${painPoints[(i + 1) % painPoints.length]}.`,
      "- Confidence labels were interpreted as medical confidence by two participants.",
      "",
      "## Follow-up needed",
      "- Test whether 'source freshness' reads as data freshness rather than clinical recency.",
    ].join("\n")));
  }
  for (let i = 1; i <= 10; i += 1) {
    manifest.push(writeFile(outputDir, `call-center/call-snippet-${String(i).padStart(2, "0")}.txt`, [
      `Call ${i}`,
      `Caller role: ${["patient", "caregiver", "care coordinator"][i % 3]}`,
      `Issue: ${painPoints[(i + 5) % painPoints.length]}.`,
      `Quote: "I do not need another reminder. I need to know which thing is actually blocking the visit."`,
      `Disposition: ${i % 2 === 0 ? "escalated to coordinator" : "resolved with manual explanation"}`,
    ].join("\n")));
  }
  for (let i = 1; i <= 6; i += 1) {
    manifest.push(writeFile(outputDir, `privacy/consent-review-${String(i).padStart(2, "0")}.md`, [
      `# Consent Review ${i}`,
      "",
      "Risk area: caregiver access and reminder content.",
      `Observed issue: ${painPoints[(i + 6) % painPoints.length]}.`,
      "Guidance: do not reveal clinical details in caregiver-safe reminders unless permission is explicit.",
      "Research implication: evaluate whether role labels are understood before expanding automated outreach.",
    ].join("\n")));
  }
  manifest.push(writeFile(outputDir, "multilingual/pt-es-reminder-examples.md", multilingualExamples()));
  manifest.push(writeFile(outputDir, "edge-cases/malformed-survey-export.csv", malformedFile()));
  manifest.push(writeFile(outputDir, "web/url-fetch-targets.md", [
    "# URL Fetch Targets for Benchmark",
    "",
    "Use these URLs in chat and task prompts to test graceful web fetching:",
    "- https://example.com/healthcare-coordination-benchmark",
    "- https://www.nngroup.com/articles/service-blueprints-definition/",
    "- https://www.w3.org/WAI/WCAG22/quickref/",
  ].join("\n")));
  manifest.push(writeMinimalPptx(outputDir, "presentations/carenav-readout.pptx"));

  const summary = {
    project: PROJECT_CONTEXT,
    generated_at: new Date().toISOString(),
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
