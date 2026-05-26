import {
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  rmSync,
  statSync,
  writeFileSync,
} from "fs";
import { basename, dirname, join, relative, resolve } from "path";
import { fileURLToPath } from "url";

const MODULE_DIR = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(MODULE_DIR, "../..");
const CANONICAL_DIR = join(MODULE_DIR, "canonical");
const SOURCES_DIR = join(CANONICAL_DIR, "sources");
const SKILLS_DIR = join(REPO_ROOT, "backend/app/skills/definitions");
const TARGET_SOURCE_COUNT = 174;

const project = {
  name: "CareNav Renewal",
  company: "Northstar Health",
  industry: "multi-site outpatient health operations",
  product: "CareNav, a patient-care coordination workspace for appointment preparation, readiness evidence, caregiver collaboration, multilingual reminders, staff handoff, and governed automation",
  stage: "end-to-end UX research program for appointment preparation, caregiver access, staff readiness queues, and evidence-grounded automation",
  business_context: "Northstar Health operates 43 clinics across community health, cardiology, oncology, pediatrics, fertility, and post-operative care. The organization piloted CareNav after missed preparation tasks increased same-day cancellations and staff manually reconciled portal messages, SMS reminders, EHR tasks, phone calls, and paper notes. The renewal program must decide which automation can be trusted, which workflows need human review, and which patient/caregiver experiences are safe to launch in multiple languages.",
  research_program: "This canonical corpus simulates a full mixed-methods UX research program: hour-long interviews, diary studies, survey exports, usability sessions, accessibility audits, journey maps, field observations, support tickets, analytics, competitor benchmarks, stakeholder memos, design briefs, discussion guides, consent/privacy notes, malformed edge cases, and report-readiness material. Sources intentionally contain contradictions, low-consensus evidence, stale metrics, multilingual ambiguity, and privacy-sensitive scenarios so tests must follow the Research Spine rather than summarizing raw data directly.",
  guardrails: [
    "Do not infer medical advice, diagnosis, treatment priority, clinical eligibility, insurance coverage, or medication guidance.",
    "Treat every participant story as synthetic PHI-like material; do not expose names, phone numbers, addresses, or unnecessary identity details in report outputs.",
    "Keep staff workflow evidence separate from patient, caregiver, administrator, and operations analyst evidence until a synthesis explicitly compares them.",
    "Flag contradictions, stale evidence, sampling gaps, language-specific wording risks, and automation-trust risks instead of smoothing them into one confident theme.",
    "Distinguish raw source evidence, evidence units, candidate atoms, accepted atoms, facts, insights, recommendations, In Review tasks, Done tasks, and Reports.",
    "Recommendations must cite source ids, exact quotes or spans where possible, codebook/reliability status, and human approval state before they become reportable.",
  ],
};

const phases = ["discover", "define", "develop", "deliver"];
const roles = ["patient", "caregiver", "care coordinator", "nurse manager", "clinic admin", "operations analyst"];
const languages = ["en", "en", "en", "es", "pt-BR"];
const clinics = ["rural clinic", "urban specialty clinic", "community health center", "pediatric clinic", "oncology clinic"];
const journeys = [
  "pre-visit lab completion",
  "caregiver invitation and consent",
  "specialist referral handoff",
  "same-day cancellation recovery",
  "post-operative checklist review",
  "multilingual reminder escalation",
  "insurance document clarification",
  "readiness dashboard triage",
];
const pains = [
  "patients cannot tell which tasks are required before the appointment",
  "staff duplicate reminders in SMS, portal messages, and handwritten notes",
  "caregivers receive partial information and then call the clinic",
  "the dashboard hides stale tasks until the day before a visit",
  "forms look complete even when lab attachments are missing",
  "Spanish and Portuguese copy is inconsistent across reminders",
  "staff do not trust automation when no source trail is shown",
  "patients miss reminders sent during working hours",
  "care coordinators need a safe way to override automation",
  "readiness statuses look final even when evidence is old",
];
const evidenceTensions = [
  "Patients say fewer reminders would reduce stress, while staff analytics show missed prep falls when reminders are repeated across SMS and portal.",
  "Care coordinators want automation to assign urgency, while nurse managers want every urgency label to show a source trail and reviewer identity.",
  "Caregivers ask for broader visibility, while patients in privacy-sensitive visits want narrow permissions and quiet notifications.",
  "Prototype A improves scan speed, while Prototype B improves source trust; neither fully solves multilingual permission wording.",
  "Survey ratings look positive for reminder clarity, while open feedback describes confusion about which tasks are required versus optional.",
  "Operations leaders want a launch recommendation, while researchers keep finding low-consensus evidence that requires reconciliation.",
  "Support tickets emphasize account access, while interviews emphasize emotional confidence and readiness trust.",
  "Accessibility audits praise information hierarchy but flag keyboard focus, contrast, and screen-reader status changes in the same flow.",
];
const sourceArtifacts = [
  "interview transcript",
  "field note",
  "support ticket export",
  "survey verbatim",
  "usability observation",
  "analytics row",
  "competitor benchmark",
  "stakeholder memo",
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
  "separate patient language from staff workflow language",
  "make every generated finding traceable to approved task evidence",
];

const sliceByMethod = {
  interview: ["interview-heavy", "coding-reliability", "low-consensus-review", "full-end-to-end"],
  "participant-profile": ["interview-heavy", "coding-reliability", "full-end-to-end"],
  diary: ["interview-heavy", "coding-reliability", "graph-synthesis", "full-end-to-end"],
  usability: ["usability-heavy", "low-consensus-review", "full-end-to-end"],
  survey: ["survey-heavy", "coding-reliability", "graph-synthesis", "full-end-to-end"],
  nps: ["survey-heavy", "full-end-to-end"],
  sus: ["survey-heavy", "full-end-to-end"],
  umux: ["survey-heavy", "full-end-to-end"],
  "card-sort": ["full-end-to-end"],
  "tree-test": ["full-end-to-end"],
  journey: ["findings-reporting", "graph-synthesis", "full-end-to-end"],
  "field-note": ["interview-heavy", "coding-reliability", "low-consensus-review", "full-end-to-end"],
  support: ["findings-reporting", "coding-reliability", "low-consensus-review", "full-end-to-end"],
  analytics: ["survey-heavy", "findings-reporting", "graph-synthesis", "full-end-to-end"],
  "ab-test": ["findings-reporting", "graph-synthesis", "full-end-to-end"],
  competitor: ["graph-synthesis", "full-end-to-end"],
  heuristic: ["accessibility-heavy", "low-consensus-review", "full-end-to-end"],
  accessibility: ["accessibility-heavy", "low-consensus-review", "full-end-to-end"],
  "laws-of-ux": ["accessibility-heavy", "full-end-to-end"],
  brief: ["graph-synthesis", "full-end-to-end"],
  stakeholder: ["findings-reporting", "graph-synthesis", "full-end-to-end"],
  plan: ["upload-smoke", "full-end-to-end"],
  guide: ["upload-smoke", "full-end-to-end"],
  consent: ["multilingual", "full-end-to-end"],
  multilingual: ["multilingual", "full-end-to-end"],
  malformed: ["malformed-edge-case", "low-consensus-review", "full-end-to-end"],
  report: ["findings-reporting", "graph-synthesis", "full-end-to-end"],
};

const baseSkillBuckets = {
  interview: ["interview_questions", "interview_analysis", "persona_creation", "empathy_map"],
  "participant-profile": ["persona_creation", "empathy_map", "stakeholder_analysis"],
  diary: ["journey_mapping", "empathy_map", "behavioral_analysis"],
  usability: ["usability_testing", "heuristic_evaluation", "cognitive_walkthrough"],
  survey: ["survey_design", "survey_analysis", "statistical_analysis"],
  nps: ["nps_analysis", "customer_satisfaction"],
  sus: ["sus_analysis", "usability_testing"],
  umux: ["umux_analysis", "usability_testing"],
  "card-sort": ["card_sorting", "information_architecture"],
  "tree-test": ["tree_testing", "information_architecture"],
  journey: ["journey_mapping", "service_blueprint", "opportunity_solution_tree"],
  "field-note": ["field_research", "contextual_inquiry", "ethnographic_analysis"],
  support: ["support_ticket_analysis", "thematic_analysis", "pain_point_analysis"],
  analytics: ["analytics_review", "funnel_analysis", "cohort_analysis"],
  "ab-test": ["ab_test_analysis", "experiment_design"],
  competitor: ["competitive_analysis", "market_research"],
  heuristic: ["heuristic_evaluation", "design_critique"],
  accessibility: ["accessibility_audit", "wcag_review"],
  "laws-of-ux": ["laws_of_ux_audit", "heuristic_evaluation"],
  brief: ["research_planning", "product_strategy"],
  stakeholder: ["stakeholder_analysis", "decision_mapping"],
  plan: ["research_planning", "recruitment_planning"],
  guide: ["discussion_guide", "interview_questions"],
  consent: ["privacy_review", "consent_review"],
  multilingual: ["localization_review", "multilingual_analysis"],
  malformed: ["data_quality_review", "parser_edge_case"],
  report: ["finding_synthesis", "reporting", "mece_synthesis"],
};

const methodPlan = [
  ["interview", 24, "discover", "md"],
  ["participant-profile", 12, "discover", "md"],
  ["diary", 10, "discover", "md"],
  ["usability", 14, "develop", "md"],
  ["survey", 8, "define", "csv"],
  ["nps", 4, "define", "csv"],
  ["sus", 4, "define", "csv"],
  ["umux", 4, "define", "csv"],
  ["card-sort", 6, "define", "csv"],
  ["tree-test", 6, "define", "csv"],
  ["journey", 6, "define", "md"],
  ["field-note", 8, "discover", "md"],
  ["support", 8, "discover", "csv"],
  ["analytics", 6, "define", "csv"],
  ["ab-test", 4, "deliver", "csv"],
  ["competitor", 5, "discover", "md"],
  ["heuristic", 5, "develop", "md"],
  ["accessibility", 5, "develop", "md"],
  ["laws-of-ux", 4, "develop", "md"],
  ["brief", 4, "discover", "md"],
  ["stakeholder", 5, "define", "md"],
  ["plan", 4, "discover", "md"],
  ["guide", 4, "discover", "md"],
  ["consent", 3, "deliver", "md"],
  ["multilingual", 4, "deliver", "md"],
  ["malformed", 3, "deliver", "csv"],
  ["report", 4, "deliver", "md"],
];

function slug(text) {
  return text.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

function discoverSkills() {
  if (!existsSync(SKILLS_DIR)) return [];
  return readdirSync(SKILLS_DIR)
    .filter((entry) => entry.endsWith(".json"))
    .map((entry) => entry.replace(/\.json$/, ""))
    .filter((name) => !name.startsWith("_"))
    .sort();
}

function selectSkills(method, index, allSkills) {
  const seeded = baseSkillBuckets[method] || [];
  const start = (index * 7) % Math.max(allSkills.length, 1);
  const dynamic = allSkills.slice(start, start + 4);
  return [...new Set([...seeded, ...dynamic])].slice(0, 8);
}

function numericId(spec) {
  return Number(spec.id.slice(3));
}

function sourceSpec(method, methodIndex, globalIndex, phase, ext, allSkills) {
  const role = roles[(globalIndex + methodIndex) % roles.length];
  const language = languages[(globalIndex + methodIndex) % languages.length];
  const clinic = clinics[(globalIndex * 2 + methodIndex) % clinics.length];
  const id = `CR-${String(globalIndex).padStart(3, "0")}`;
  const title = `${project.name} ${method.replace(/-/g, " ")} source ${String(methodIndex).padStart(2, "0")}`;
  const file = `${id}-${slug(method)}-${String(methodIndex).padStart(2, "0")}.${ext}`;
  return {
    id,
    title,
    method,
    phase,
    file_type: ext,
    role,
    language,
    clinic,
    participant_ids: [`P${String(((globalIndex - 1) % 48) + 1).padStart(2, "0")}`],
    relative_path: join("sources", method, file),
    slices: [...new Set([...(sliceByMethod[method] || ["full-end-to-end"]), "full-end-to-end"])],
    tags: [method, phase, role, language, clinic.replace(/\s+/g, "-")],
    skills: selectSkills(method, globalIndex, allSkills),
  };
}

function sourceDepth(method) {
  if (method === "interview") return 132;
  if (method === "usability") return 72;
  if (method === "competitor" || method === "accessibility" || method === "heuristic") return 54;
  if (method === "brief" || method === "stakeholder" || method === "report") return 48;
  if (method === "diary" || method === "field-note") return 42;
  return 28;
}

function methodFrame(spec) {
  const method = spec.method.replace(/-/g, " ");
  if (spec.method === "interview") {
    return {
      title: "One-hour interview transcript",
      unit: "timestamped interview segment",
      analyst: "Moderator probes for concrete examples, emotional language, workflow workarounds, and contradictions.",
    };
  }
  if (spec.method === "usability") {
    return {
      title: "Moderated usability test",
      unit: "task observation",
      analyst: "Observer records task success, scan behavior, hesitation, accessibility friction, and source-trail comprehension.",
    };
  }
  if (spec.file_type === "csv") {
    return {
      title: `${method} export`,
      unit: "row-level record",
      analyst: "Analyst should inspect metric definitions, segment cuts, verbatim text, and sampling limitations before synthesizing.",
    };
  }
  return {
    title: `${method} research source`,
    unit: "evidence note",
    analyst: "Analyst should preserve exact source context, method limits, contradictions, and report-readiness gates.",
  };
}

function evidenceBlock(spec, section) {
  const id = numericId(spec);
  const pain = pains[(id + section) % pains.length];
  const second = pains[(id + section + 4) % pains.length];
  const opportunity = opportunities[(id + section) % opportunities.length];
  const tension = evidenceTensions[(id + section) % evidenceTensions.length];
  const journey = journeys[(id + section) % journeys.length];
  const artifact = sourceArtifacts[(id + section) % sourceArtifacts.length];
  const participant = `P${String(((id + section) % 48) + 1).padStart(2, "0")}`;
  const minute = String(Math.min(59, Math.floor((section - 1) * 60 / Math.max(sourceDepth(spec.method), 1)))).padStart(2, "0");
  const secondMark = String((section * 17) % 60).padStart(2, "0");
  return [
    `## Evidence unit candidate ${section}: ${journey}`,
    "",
    `Source position: [${minute}:${secondMark}] in ${methodFrame(spec).title}; candidate participant ${participant}; role ${spec.role}; language ${spec.language}; clinic ${spec.clinic}.`,
    `Observed moment: ${pain}. The participant or operational record describes the issue while moving through ${journey}, and the note explicitly connects the issue to appointment preparation, readiness evidence, or caregiver-safe coordination.`,
    `Thick description: The team member first checks the dashboard, then cross-references another ${artifact}, and then decides whether the readiness status is safe enough to act on. The source describes how the person looks for freshness, owner, evidence source, permission status, and whether an automated recommendation has been reviewed. The detail matters because a generic summary such as "users want clarity" would hide the difference between evidence traceability, emotional reassurance, workflow speed, and clinical safety boundaries.`,
    `Direct quote: "I can only approve a recommendation when the system shows which task, transcript, ticket, or survey row produced it; otherwise I have to rebuild the story myself before I trust the status."`,
    `Counter-signal: ${second}. ${tension} This contradiction is intentional canonical material for reliability, debate, reconciliation, and low-consensus review tests.`,
    `Coding hints: likely open codes include evidence traceability, readiness confidence, caregiver boundary, multilingual risk, staff override, stale-source concern, task priority ambiguity, and automation trust. Coders should decide independently, cite spans, record confidence, and memo ambiguity before reliability is computed.`,
    `Implication candidate: ${opportunity}. This is only a candidate implication until source-grounded multi-model extraction, coding, reliability or reconciliation, human review, and Done-task gates accept it.`,
    `Report gate reminder: raw source material is not report-ready. Any future nugget, fact, insight, recommendation, design decision, or report paragraph must preserve the source id ${spec.id}, evidence-unit location, codebook version, route evidence, review state, and task approval path.`,
    "",
  ].join("\n");
}

function repeatedEvidence(spec) {
  const paragraphs = [];
  for (let section = 1; section <= sourceDepth(spec.method); section += 1) {
    paragraphs.push(evidenceBlock(spec, section));
  }
  return paragraphs.join("\n");
}

function markdownContent(spec) {
  const frame = methodFrame(spec);
  return [
    `# ${spec.title}`,
    "",
    `Project: ${project.name}`,
    `Company: ${project.company}`,
    `Business context: ${project.business_context}`,
    `Research program: ${project.research_program}`,
    `Method: ${spec.method}`,
    `Source frame: ${frame.title}`,
    `Evidence unit model: ${frame.unit}`,
    `Double Diamond phase: ${spec.phase}`,
    `Participant ids: ${spec.participant_ids.join(", ")}`,
    `Primary role: ${spec.role}`,
    `Clinic: ${spec.clinic}`,
    `Language: ${spec.language}`,
    `Journey focus: ${journeys[numericId(spec) % journeys.length]}`,
    "",
    "## Source-specific protocol notes",
    "",
    frame.analyst,
    "Do not use this file as a ready-made finding. Segment stable evidence units from the raw source, run independent extraction and open coding, compare source span, claim, code, model identity, and route evidence, then move low-consensus claims to reconciliation before any atomic research artifact becomes trusted.",
    "",
    "## Project guardrails carried into this source",
    "",
    ...project.guardrails.map((guardrail) => `- ${guardrail}`),
    "",
    repeatedEvidence(spec),
    "## Analyst memo",
    "",
    `This synthetic source supports ${spec.skills.slice(0, 5).join(", ")} coverage.`,
    "The source includes messy but plausible UX research evidence and must be interpreted with source traceability, codebook criteria, item-level reliability, and human review.",
  ].join("\n");
}

function csvContent(spec) {
  const rows = [
    "record_id,participant_id,role,language,clinic,journey,metric,value,confidence,open_feedback,contradiction,source_note,report_ready,required_gate",
  ];
  for (let row = 1; row <= 220; row += 1) {
    const id = numericId(spec);
    const pain = pains[(row + id) % pains.length];
    const opportunity = opportunities[(row + 3) % opportunities.length];
    const tension = evidenceTensions[(row + id) % evidenceTensions.length];
    rows.push([
      `${spec.id}-R${String(row).padStart(3, "0")}`,
      `P${String(((row + id) % 48) + 1).padStart(2, "0")}`,
      roles[row % roles.length],
      languages[row % languages.length],
      clinics[(row + id) % clinics.length],
      `"${journeys[(row + id) % journeys.length]}"`,
      spec.method,
      1 + ((row + id) % 7),
      ["low", "medium", "high"][(row + id) % 3],
      `"${pain}; requested ${opportunity}; source says the decision cannot be trusted without source freshness, owner, and review state."`,
      `"${tension}"`,
      `"Synthetic ${project.name} corpus row. Preserve participant, method, language, journey, metric definition, and review state."`,
      "false",
      `"source evidence unit -> independent extraction/coding -> reliability/reconciliation -> Done task approval"`,
    ].join(","));
  }
  return rows.join("\n");
}

function supportCsvContent(spec) {
  const rows = [
    "ticket_id,project,method,phase,role,language,issue,opportunity,report_ready,approval_requirement",
  ];
  for (let row = 1; row <= 180; row += 1) {
    const id = numericId(spec);
    rows.push([
      `${spec.id}-T${String(row).padStart(3, "0")}`,
      project.name,
      spec.method,
      spec.phase,
      roles[row % roles.length],
      languages[row % languages.length],
      `"${pains[(row + id) % pains.length]} during ${journeys[(row + id) % journeys.length]}"`,
      `"${opportunities[(row + id) % opportunities.length]}"`,
      "false",
      `"Only findings derived from approved Done tasks may feed Reports."`,
    ].join(","));
  }
  return rows.join("\n");
}

function contentFor(spec) {
  if (spec.method === "support") return supportCsvContent(spec);
  if (spec.file_type === "csv") return csvContent(spec);
  return markdownContent(spec);
}

function manifestEntry(spec, absolutePath) {
  const stats = statSync(absolutePath);
  const content = readFileSync(absolutePath, "utf8");
  const wordCount = content.trim().split(/\s+/).filter(Boolean).length;
  return {
    ...spec,
    path: spec.relative_path,
    bytes: stats.size,
    word_count: wordCount,
    long_form: stats.size >= 1000,
    synthetic: true,
    project: project.name,
    report_readiness: "raw_source_not_report_ready_until_done_task_approval",
    intended_use: "canonical_product_level_synthetic_ux_research",
  };
}

function writeJson(path, value) {
  writeFileSync(path, `${JSON.stringify(value, null, 2)}\n`);
}

function buildSources() {
  const skills = discoverSkills();
  const specs = [];
  let globalIndex = 1;
  for (const [method, count, phase, ext] of methodPlan) {
    for (let i = 1; i <= count; i += 1) {
      specs.push(sourceSpec(method, i, globalIndex, phase, ext, skills));
      globalIndex += 1;
    }
  }
  if (specs.length !== TARGET_SOURCE_COUNT) {
    throw new Error(`Expected ${TARGET_SOURCE_COUNT} sources but planned ${specs.length}`);
  }

  const manifest = [];
  for (const spec of specs) {
    const absolutePath = join(CANONICAL_DIR, spec.relative_path);
    mkdirSync(dirname(absolutePath), { recursive: true });
    writeFileSync(absolutePath, contentFor(spec));
    manifest.push(manifestEntry(spec, absolutePath));
  }
  return { manifest, skills };
}

function skillCoverage(manifest, skills) {
  const coverage = {};
  for (const skill of skills) {
    const matching = manifest.filter((entry) => entry.skills.includes(skill));
    coverage[skill] = {
      source_count: matching.length,
      slices: [...new Set(matching.flatMap((entry) => entry.slices))].sort(),
      methods: [...new Set(matching.map((entry) => entry.method))].sort(),
      example_sources: matching.slice(0, 5).map((entry) => entry.id),
    };
  }
  return {
    project: project.name,
    total_skills: skills.length,
    covered_skills: Object.values(coverage).filter((entry) => entry.source_count > 0).length,
    coverage,
  };
}

function sliceSummary(manifest) {
  const summary = {};
  for (const entry of manifest) {
    for (const slice of entry.slices) {
      summary[slice] ||= { source_count: 0, methods: new Set(), phases: new Set() };
      summary[slice].source_count += 1;
      summary[slice].methods.add(entry.method);
      summary[slice].phases.add(entry.phase);
    }
  }
  return Object.fromEntries(Object.entries(summary).map(([slice, value]) => [slice, {
    source_count: value.source_count,
    methods: [...value.methods].sort(),
    phases: [...value.phases].sort(),
  }]));
}

function writeDocs(manifest, skills) {
  const slices = sliceSummary(manifest);
  const totalWords = manifest.reduce((sum, entry) => sum + (entry.word_count || 0), 0);
  const averageWords = Math.round(totalWords / Math.max(manifest.length, 1));
  const deepSources = manifest.filter((entry) => (entry.word_count || 0) >= 10000).length;
  writeFileSync(join(CANONICAL_DIR, "README.md"), [
    "# Canonical Synthetic UX Research Corpus",
    "",
    "This committed corpus is Istara's source of truth for product-level synthetic research tests.",
    "",
    `Project: ${project.name}`,
    `Source count: ${manifest.length}`,
    `Long-form sources: ${manifest.filter((entry) => entry.long_form).length}`,
    `Approximate total words: ${totalWords.toLocaleString("en-US")}`,
    `Average words per source: ${averageWords.toLocaleString("en-US")}`,
    `Sources with at least 10,000 words/row-word equivalents: ${deepSources}`,
    `Skill definitions covered by manifest: ${skills.length}`,
    "",
    "## Contract",
    "",
    "- Product-level document, research, task, Findings, Reports, benchmark, simulation, eval, and marathon tests use this corpus or a manifest-backed named slice.",
    "- Canonical sources must remain compatible with Istara upload/processable file types so benchmark failures test product behavior, not bad fixture formats.",
    "- Tiny ad hoc fixtures are allowed only for parser/unit tests and must be labeled as unit fixtures.",
    "- Raw corpus sources are not report-ready evidence. Reports are generated only from Findings derived from approved Done tasks.",
    "- The corpus is fully synthetic and contains no private data.",
    "- The corpus is intentionally large enough to stress retrieval, coding, task review, summarization, report gating, and multi-model route evidence.",
    "",
    "## Named slices",
    "",
    ...Object.entries(slices).map(([slice, value]) => `- ${slice}: ${value.source_count} sources across ${value.methods.join(", ")}`),
    "",
    "## Regeneration",
    "",
    "Run `node tests/document_corpus/generate-canonical-corpus.mjs` from the repo root after intentional corpus contract changes.",
  ].join("\n"));

  writeFileSync(join(CANONICAL_DIR, "playbook.md"), [
    "# Canonical Corpus Playbook",
    "",
    "Use `tests/document_corpus/shared-corpus.mjs` rather than reading this folder directly. The helper exposes manifest-backed selectors so tests can ask for `interview-heavy`, `survey-heavy`, `usability-heavy`, `accessibility-heavy`, `findings-reporting`, `multilingual`, `malformed-edge-case`, `upload-smoke`, `coding-reliability`, `graph-synthesis`, `low-consensus-review`, or `full-end-to-end` material.",
    "",
    "Historical slash-style aliases such as `findings/reporting` and `malformed/edge-case` are normalized by the shared helper; manifests store canonical hyphenated names.",
    "",
    "## Research process",
    "",
    "The synthetic program follows a Double Diamond flow: discover sources capture interviews, diary studies, support tickets, and field notes; define sources capture surveys, card sorting, tree testing, analytics, and stakeholder tensions; develop sources capture usability, heuristic, accessibility, and Laws of UX work; deliver sources capture A/B tests, privacy review, multilingual review, malformed exports, and report-readiness material.",
    "Support-ticket exports are represented as CSV in the canonical upload path because `.jsonl` is not an Istara document upload format.",
    "",
    "## Evidence flow",
    "",
    "Tests should upload or ingest these sources, create or execute research tasks, let agent outputs move into review, and only treat findings as report-eligible after humans approve the task into Done.",
    "",
    "## Speed guidance",
    "",
    "Use a named slice for focused tests and reserve `full-end-to-end` for benchmark, marathon, and representative document-heavy scenarios.",
  ].join("\n"));

  writeJson(join(CANONICAL_DIR, "expected-evidence-chain.json"), {
    project: project.name,
    corpus_depth: {
      total_sources: manifest.length,
      total_words: totalWords,
      average_words_per_source: averageWords,
      sources_with_at_least_10000_words: deepSources,
    },
    rules: [
      "Raw corpus sources are not directly report-ready.",
      "Agent task outputs may create findings, nuggets, facts, insights, and recommendations.",
      "Tasks in Backlog, To Do, In Progress, or In Review are not report eligible.",
      "Only approved Done tasks may contribute task-bound findings to Reports.",
      "Reports should cite source ids, task ids, finding ids, and approval state.",
    ],
    example_flow: [
      "Upload canonical corpus slice.",
      "Create project-scoped research task.",
      "Run agent/skill work against documents.",
      "Review task output and route back if evidence is weak.",
      "Approve task to Done when evidence is sufficient.",
      "Generate Findings and Reports from approved evidence only.",
    ],
  });
}

function main() {
  rmSync(CANONICAL_DIR, { recursive: true, force: true });
  mkdirSync(SOURCES_DIR, { recursive: true });
  const { manifest, skills } = buildSources();
  writeJson(join(CANONICAL_DIR, "manifest.json"), {
    version: 1,
    generated_by: "tests/document_corpus/generate-canonical-corpus.mjs",
    project,
    total_sources: manifest.length,
    long_form_sources: manifest.filter((entry) => entry.long_form).length,
    total_words: manifest.reduce((sum, entry) => sum + (entry.word_count || 0), 0),
    average_words_per_source: Math.round(
      manifest.reduce((sum, entry) => sum + (entry.word_count || 0), 0) / Math.max(manifest.length, 1),
    ),
    slices: sliceSummary(manifest),
    sources: manifest,
  });
  writeJson(join(CANONICAL_DIR, "skill-coverage-map.json"), skillCoverage(manifest, skills));
  writeDocs(manifest, skills);
  console.log(`Generated ${manifest.length} canonical sources in ${relative(REPO_ROOT, CANONICAL_DIR)}`);
}

main();
