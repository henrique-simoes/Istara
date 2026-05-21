import {
  existsSync,
  mkdirSync,
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
  product: "patient-care coordination workspace",
  stage: "end-to-end UX research program for appointment preparation, caregiver access, staff readiness queues, and evidence-grounded automation",
};

const phases = ["discover", "define", "develop", "deliver"];
const roles = ["patient", "caregiver", "care coordinator", "nurse manager", "clinic admin", "operations analyst"];
const languages = ["en", "en", "en", "es", "pt-BR"];
const clinics = ["rural clinic", "urban specialty clinic", "community health center", "pediatric clinic", "oncology clinic"];
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
  interview: ["interview-heavy", "full-end-to-end"],
  "participant-profile": ["interview-heavy", "full-end-to-end"],
  diary: ["interview-heavy", "full-end-to-end"],
  usability: ["usability-heavy", "full-end-to-end"],
  survey: ["survey-heavy", "full-end-to-end"],
  nps: ["survey-heavy", "full-end-to-end"],
  sus: ["survey-heavy", "full-end-to-end"],
  umux: ["survey-heavy", "full-end-to-end"],
  "card-sort": ["full-end-to-end"],
  "tree-test": ["full-end-to-end"],
  journey: ["findings-reporting", "full-end-to-end"],
  "field-note": ["interview-heavy", "full-end-to-end"],
  support: ["findings-reporting", "full-end-to-end"],
  analytics: ["survey-heavy", "findings-reporting", "full-end-to-end"],
  "ab-test": ["findings-reporting", "full-end-to-end"],
  competitor: ["full-end-to-end"],
  heuristic: ["accessibility-heavy", "full-end-to-end"],
  accessibility: ["accessibility-heavy", "full-end-to-end"],
  "laws-of-ux": ["accessibility-heavy", "full-end-to-end"],
  brief: ["full-end-to-end"],
  stakeholder: ["findings-reporting", "full-end-to-end"],
  plan: ["upload-smoke", "full-end-to-end"],
  guide: ["upload-smoke", "full-end-to-end"],
  consent: ["multilingual", "full-end-to-end"],
  multilingual: ["multilingual", "full-end-to-end"],
  malformed: ["malformed-edge-case", "full-end-to-end"],
  report: ["findings-reporting", "full-end-to-end"],
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
  ["support", 8, "discover", "jsonl"],
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

function repeatedEvidence(spec) {
  const paragraphs = [];
  for (let section = 1; section <= 8; section += 1) {
    const pain = pains[(Number(spec.id.slice(3)) + section) % pains.length];
    const second = pains[(Number(spec.id.slice(3)) + section + 4) % pains.length];
    const opportunity = opportunities[(Number(spec.id.slice(3)) + section) % opportunities.length];
    paragraphs.push([
      `## Evidence block ${section}`,
      "",
      `Role and context: ${spec.role} in a ${spec.clinic}; language ${spec.language}.`,
      `Observed issue: ${pain}.`,
      `Counter-signal: ${second}. This source intentionally includes tension so synthesis must weigh contradictions instead of averaging them away.`,
      `Quote: "I can only approve a recommendation when the system shows which task, transcript, or ticket produced it."`,
      `Implication: ${opportunity}.`,
      "Reporting rule: this raw source is not report-ready until a human-approved Done task turns it into a finding with evidence citations.",
      "",
    ].join("\n"));
  }
  return paragraphs.join("\n");
}

function markdownContent(spec) {
  return [
    `# ${spec.title}`,
    "",
    `Project: ${project.name}`,
    `Company: ${project.company}`,
    `Method: ${spec.method}`,
    `Double Diamond phase: ${spec.phase}`,
    `Participant ids: ${spec.participant_ids.join(", ")}`,
    `Primary role: ${spec.role}`,
    `Clinic: ${spec.clinic}`,
    `Language: ${spec.language}`,
    "",
    repeatedEvidence(spec),
    "## Analyst memo",
    "",
    `This synthetic source supports ${spec.skills.slice(0, 5).join(", ")} coverage.`,
    "The source includes messy but plausible UX research evidence and must be interpreted with source traceability.",
  ].join("\n");
}

function csvContent(spec) {
  const rows = [
    "record_id,participant_id,role,language,metric,value,open_feedback,source_note",
  ];
  for (let row = 1; row <= 80; row += 1) {
    const pain = pains[(row + Number(spec.id.slice(3))) % pains.length];
    const opportunity = opportunities[(row + 3) % opportunities.length];
    rows.push([
      `${spec.id}-R${String(row).padStart(3, "0")}`,
      `P${String(((row + Number(spec.id.slice(3))) % 48) + 1).padStart(2, "0")}`,
      roles[row % roles.length],
      languages[row % languages.length],
      spec.method,
      1 + ((row + Number(spec.id.slice(3))) % 7),
      `"${pain}; requested ${opportunity}"`,
      `"Synthetic ${project.name} corpus. Not report-ready until approved Done task evidence."`,
    ].join(","));
  }
  return rows.join("\n");
}

function jsonlContent(spec) {
  const lines = [];
  for (let row = 1; row <= 65; row += 1) {
    lines.push(JSON.stringify({
      record_id: `${spec.id}-J${String(row).padStart(3, "0")}`,
      project: project.name,
      method: spec.method,
      phase: spec.phase,
      role: roles[row % roles.length],
      language: languages[row % languages.length],
      issue: pains[(row + Number(spec.id.slice(3))) % pains.length],
      opportunity: opportunities[(row + Number(spec.id.slice(3))) % opportunities.length],
      report_ready: false,
      approval_requirement: "Only findings derived from approved Done tasks may feed Reports.",
    }));
  }
  return lines.join("\n");
}

function contentFor(spec) {
  if (spec.file_type === "csv") return csvContent(spec);
  if (spec.file_type === "jsonl") return jsonlContent(spec);
  return markdownContent(spec);
}

function manifestEntry(spec, absolutePath) {
  const stats = statSync(absolutePath);
  return {
    ...spec,
    path: spec.relative_path,
    bytes: stats.size,
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
  writeFileSync(join(CANONICAL_DIR, "README.md"), [
    "# Canonical Synthetic UX Research Corpus",
    "",
    "This committed corpus is Istara's source of truth for product-level synthetic research tests.",
    "",
    `Project: ${project.name}`,
    `Source count: ${manifest.length}`,
    `Long-form sources: ${manifest.filter((entry) => entry.long_form).length}`,
    `Skill definitions covered by manifest: ${skills.length}`,
    "",
    "## Contract",
    "",
    "- Product-level document, research, task, Findings, Reports, benchmark, simulation, eval, and marathon tests use this corpus or a manifest-backed named slice.",
    "- Tiny ad hoc fixtures are allowed only for parser/unit tests and must be labeled as unit fixtures.",
    "- Raw corpus sources are not report-ready evidence. Reports are generated only from Findings derived from approved Done tasks.",
    "- The corpus is fully synthetic and contains no private data.",
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
    "Use `tests/document_corpus/shared-corpus.mjs` rather than reading this folder directly. The helper exposes manifest-backed selectors so tests can ask for `interview-heavy`, `survey-heavy`, `usability-heavy`, `accessibility-heavy`, `findings-reporting`, `multilingual`, `malformed-edge-case`, `upload-smoke`, or `full-end-to-end` material.",
    "",
    "## Research process",
    "",
    "The synthetic program follows a Double Diamond flow: discover sources capture interviews, diary studies, support tickets, and field notes; define sources capture surveys, card sorting, tree testing, analytics, and stakeholder tensions; develop sources capture usability, heuristic, accessibility, and Laws of UX work; deliver sources capture A/B tests, privacy review, multilingual review, malformed exports, and report-readiness material.",
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
    slices: sliceSummary(manifest),
    sources: manifest,
  });
  writeJson(join(CANONICAL_DIR, "skill-coverage-map.json"), skillCoverage(manifest, skills));
  writeDocs(manifest, skills);
  console.log(`Generated ${manifest.length} canonical sources in ${relative(REPO_ROOT, CANONICAL_DIR)}`);
}

main();
