#!/usr/bin/env python3
"""Generate Istara SFT datasets from the live skill definitions.

The script intentionally defaults to local-only generation. Use --upload only when
Hugging Face credentials are configured and a dataset push is intended.
"""

from __future__ import annotations

import argparse
import json
import random
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ID = "henrique-simoes/ux-research-strategy-dataset"
ROOT = Path(__file__).resolve().parent
SKILLS_DIR = ROOT.parent / "backend" / "app" / "skills" / "definitions"
DEFAULT_OUT_DIR = ROOT / "generated_datasets"
RANDOM = random.Random(42)

SYSTEM_PROMPT = """You are an expert UX Research Agent operating within Istara.
Your primary directive is methodological rigor. You do not hallucinate summaries;
you synthesize evidence.

Core doctrine:
1. Atomic Research: raw observations become Nuggets, Nuggets support Facts, Facts support Insights, Insights support Recommendations.
2. Every analytical claim must be grounded in evidence.
3. State the method in <research_methodology> before final JSON.
4. Output valid JSON matching the requested strict schema.
5. Never invent fields outside the schema."""

from consolidated_bank import NUGGET_BANK

PRODUCT_CONTEXTS = [
    "B2B research repository used by product teams",
    "mobile onboarding flow for a fintech app",
    "healthcare appointment booking portal",
    "enterprise analytics dashboard",
    "collaborative whiteboarding workspace",
    "survey and interview operations console",
    "e-commerce checkout funnel for a fast-fashion brand",
    "SaaS dashboard for IT server monitoring",
    "consumer-facing meditation and sleep tracking app",
    "B2B CRM interface for enterprise sales teams",
    "public transit ticketing and routing mobile app",
    "patient portal for a regional hospital network",
    "crypto exchange trading view and portfolio tracker",
    "internal HR portal for employee benefits and time-off",
    "real estate search platform with 3D tours",
    "educational app for elementary school math",
    "B2Gov tax filing and document submission platform",
    "freelance marketplace matching platform",
    "ride-sharing driver app and route planner",
    "heavy machinery predictive maintenance dashboard",
    "streaming video service content discovery interface",
    "smart home device management and automation app",
    "grocery delivery storefront and order tracker",
    "enterprise cybersecurity threat detection center",
    "AI-powered coding assistant plugin interface",
    "legal document review and contract lifecycle tool",
    "cloud infrastructure provisioning console",
    "fitness tracking wearable companion app",
    "restaurant point-of-sale and kitchen display system",
    "automotive infotainment and navigation system",
    "social media feed and content creation studio",
    "logistics and supply chain inventory management dashboard",
    "telehealth video consultation platform",
    "peer-to-peer mobile payment application",
    "virtual event and webinar hosting platform",
    "podcast hosting and monetization platform",
    "travel booking and itinerary management portal",
    "smart city sensor network data visualization tool",
    "online multiplayer game matchmaking interface",
    "agricultural crop yield prediction and tracking software",
    "non-profit donation and volunteer management system",
    "supply chain risk management dashboard",
    "academic research publication database",
    "smart watch fitness and vitals tracking interface",
    "warehouse inventory barcode scanning app",
    "commercial aircraft cabin management interface",
    "drone flight control and telemetry dashboard",
    "John Deere tractor IoT monitoring and diagnostics app",
    "agricultural chemical supply chain tracker",
    "airline crew scheduling and logistics app",
    "passenger mobile boarding and flight management app",
    "automotive dealership inventory and financing software",
    "electric vehicle battery analytics and charging portal",
    "corporate treasury management system for global banking",
    "retail banking consumer app with algorithmic trading",
    "global food distribution logistics system",
    "brewery fermentation monitoring and quality control dashboard",
    "chemical plant safety and compliance reporting tool",
    "polymer formulation lab notebook and experiment tracker",
    "offshore oil rig predictive maintenance panel",
    "smart grid energy distribution map for utilities",
    "clinical trial patient symptom and adherence tracker",
    "pharmaceutical drug discovery molecular visualization tool",
    "auto insurance claims adjustor mobile app",
    "life insurance actuarial risk assessment dashboard",
    "factory floor robotics control interface",
    "semiconductor cleanroom air quality and yield monitor",
    "big-box retailer supplier portal and EDI interface",
    "omnichannel retail customer data platform",
    "5G network topology visualization tool",
    "telecom field technician dispatch and diagnostic app",
    "freight train cargo manifest and routing system",
    "maritime shipping container global tracker",
    "water treatment plant SCADA control system",
    "residential solar panel energy generation and net metering app",
    "commercial real estate property management dashboard",
    "wholesale distribution pricing and margin optimization tool",
    "aerospace engineering CAD version control platform",
    "global metals and mining resource allocation planner",
]

METHOD_HINTS = {
    "ab-test": "Kohavi, Tang & Xu online controlled experiments",
    "accessibility": "WCAG 2.2 and WCAG-EM",
    "affinity": "Beyer & Holtzblatt affinity diagramming",
    "analytics": "behavioral analytics review and funnel diagnosis",
    "anova": "Analysis of Variance (ANOVA) for A/B/n testing and group comparisons",
    "bayes": "Bayesian hierarchical modeling for small-sample usability testing",
    "browser": "browser-grounded UX inspection",
    "card": "open and closed card sorting",
    "clickstream": "Markov chains and sequential pattern mining for clickstream analysis",
    "cluster": "K-means and hierarchical cluster analysis for behavioral segmentation",
    "cognitive": "Wharton cognitive walkthrough",
    "competitive": "competitive benchmarking and UX heuristics",
    "concept": "concept testing and desirability evaluation",
    "conjoint": "Conjoint analysis for pricing and feature trade-offs",
    "contextual": "contextual inquiry",
    "delphi": "Delphi method for expert consensus forecasting",
    "design-critique": "formal design critique and heuristic evaluation",
    "design-system": "design system audit and token consistency check",
    "desk-research": "secondary research and literature review",
    "diary": "diary study longitudinal analysis",
    "eeg": "EEG event-related potentials (ERPs) in HCI research",
    "empathy": "empathy mapping and user modeling",
    "ethnography": "Grounded theory methodology for qualitative ethnographic data",
    "evaluate": "research quality evaluation and meta-analysis",
    "eye-tracking": "Eye-tracking heatmaps and saccade pathway analysis",
    "factor": "Factor analysis and PCA for psychometric questionnaire validation",
    "field": "ethnographic field studies and contextual observation",
    "fitts": "Fitts's Law predictive modeling for interaction pointing time",
    "goms": "GOMS (Goals, Operators, Methods, and Selection rules) cognitive modeling",
    "handoff": "design-to-development handoff documentation",
    "heuristic": "Nielsen heuristic evaluation",
    "hmw": "How Might We statement ideation and reframing",
    "interview": "semi-structured interview methodology",
    "item-response": "Item Response Theory (IRT) for adaptive UX survey design",
    "journey": "journey mapping",
    "jtbd": "Christensen JTBD and Ulwick ODI",
    "kappa": "intercoder reliability and Cohen's kappa",
    "keystroke": "Keystroke-Level Model (KLM) for expert user execution time",
    "longitudinal": "longitudinal tracking and behavioral cohort analysis",
    "markov": "Hidden Markov Models (HMM) for user state inference",
    "maxdiff": "MaxDiff (Maximum Difference) scaling for feature prioritization",
    "monte-carlo": "Monte Carlo simulations for estimating task success probabilities",
    "multidimensional": "Multidimensional scaling (MDS) for perceptual mapping",
    "netnography": "Netnography and online community observational research",
    "nps": "Net Promoter Score analysis",
    "participant": "participant simulation and behavioral modeling",
    "persona": "evidence-based persona creation",
    "physiological": "GSR and HR physiological sensor data analysis for cognitive load",
    "prioritization": "feature prioritization matrix (e.g., RICE, Kano)",
    "prototype": "rapid prototype usability testing and feedback",
    "pupillometry": "Pupillometry and blink rate analysis for attention measurement",
    "q-methodology": "Q-methodology for measuring subjective viewpoints",
    "regression": "UX regression impact analysis",
    "regression-stats": "Linear and logistic regression modeling for user behavior prediction",
    "repository": "research repository curation and taxonomy management",
    "research-synthesis": "Noblit & Hare meta-ethnography and Atomic Research",
    "retro": "research operations retrospective",
    "sentiment": "NLP-based sentiment analysis and topic modeling on open-ended feedback",
    "stakeholder": "stakeholder interviews and business alignment",
    "stitch": "UI stitching and component-level design review",
    "structural-equation": "Structural Equation Modeling (SEM) for complex UX constructs",
    "survey": "survey methodology and response analysis",
    "survival": "Survival analysis and Kaplan-Meier curves for user retention and churn",
    "sus": "System Usability Scale (SUS) and UMUX-Lite scoring",
    "system-dynamics": "System dynamics modeling for complex sociotechnical systems",
    "task": "quantitative task analysis and time-on-task measurement",
    "taxonomy": "information architecture taxonomy generation",
    "thematic": "Braun & Clarke reflexive thematic analysis",
    "transcribe": "audio transcription and thematic coding",
    "tree": "tree testing and findability analysis",
    "triangulation": "Mixed-methods data triangulation and convergence analysis",
    "usability": "task-based usability testing",
    "user-flow": "user flow mapping and interaction modeling",
    "ux-law": "UX laws (e.g., Fitts's, Hick's) compliance check",
    "workshop": "collaborative workshop facilitation and synthesis",
}


@dataclass(frozen=True)
class SkillDefinition:
    name: str
    display_name: str
    description: str
    phase: str
    skill_type: str
    plan_prompt: str
    execute_prompt: str
    output_schema_text: str
    output_schema: Any
    strict_schema: dict[str, Any]
    source_path: Path


def make_schema_strict(schema: Any) -> dict[str, Any]:
    """Match Istara's runtime strict-schema behavior without importing app code."""
    if not isinstance(schema, (dict, list)):
        if isinstance(schema, bool):
            return {"type": "boolean"}
        if isinstance(schema, int):
            return {"type": "integer"}
        if isinstance(schema, float):
            return {"type": "number"}
        return {"type": "string"}

    if isinstance(schema, list):
        item_example = schema[0] if schema else "..."
        return {"type": "array", "items": make_schema_strict(item_example)}

    if "type" in schema:
        strict = dict(schema)
        schema_type = strict.get("type")
        if schema_type == "object":
            properties = strict.get("properties", {})
            strict["additionalProperties"] = False
            strict["properties"] = {key: make_schema_strict(value) for key, value in properties.items()}
            strict["required"] = list(properties.keys())
        elif schema_type == "array":
            strict["items"] = make_schema_strict(strict.get("items", "item"))
        return strict

    return {
        "type": "object",
        "properties": {key: make_schema_strict(value) for key, value in schema.items()},
        "required": list(schema.keys()),
        "additionalProperties": False,
    }


def load_skill_definitions(skills_dir: Path = SKILLS_DIR) -> list[SkillDefinition]:
    skills: list[SkillDefinition] = []
    for path in sorted(skills_dir.glob("*.json")):
        if path.name.startswith("_"):
            continue
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or raw.get("enabled") is False:
            continue
        schema_text = raw.get("output_schema") or "{}"
        output_schema = parse_output_schema(schema_text, path)
        skills.append(
            SkillDefinition(
                name=raw["name"],
                display_name=raw.get("display_name", raw["name"]),
                description=raw.get("description", ""),
                phase=raw.get("phase", "unknown"),
                skill_type=raw.get("skill_type", "mixed"),
                plan_prompt=raw.get("plan_prompt", ""),
                execute_prompt=raw.get("execute_prompt", ""),
                output_schema_text=schema_text,
                output_schema=output_schema,
                strict_schema=make_schema_strict(output_schema),
                source_path=path,
            )
        )
    return skills


def parse_output_schema(schema_text: str, path: Path) -> Any:
    """Parse production schema text, tolerating legacy numeric range examples."""
    try:
        return json.loads(schema_text)
    except json.JSONDecodeError:
        normalized = re.sub(r":\s*-?\d+(?:\.\d+)?\s*-\s*-?\d+(?:\.\d+)?", ": 0", schema_text)
        try:
            return json.loads(normalized)
        except json.JSONDecodeError:
            print(f"Warning: {path.name} has non-JSON output_schema text; using generic strict research schema.")
            return {
                "summary": f"Schema fallback for {path.stem}",
                "nuggets": [{"text": "verbatim evidence", "source": "source", "tags": ["tag"]}],
                "facts": [{"text": "verified pattern", "supporting_nuggets": ["verbatim evidence"]}],
                "insights": [{"text": "interpretive conclusion", "confidence": "medium"}],
                "recommendations": [{"text": "actionable recommendation", "priority": "medium"}],
                "schema_note": "Original skill definition contains non-JSON schema shorthand.",
            }


def tool_for_skill(skill: SkillDefinition) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": skill.name,
            "description": skill.description[:900],
            "parameters": skill.strict_schema,
        },
    }


def research_context(skill: SkillDefinition) -> str:
    nuggets = RANDOM.sample(NUGGET_BANK, 4)
    source_lines = "\n".join(f'[{source}] "{text}"' for text, source, _tags in nuggets)
    return (
        f"Product context: {RANDOM.choice(PRODUCT_CONTEXTS)}.\n"
        f"Research phase: {skill.phase}. Skill type: {skill.skill_type}.\n"
        f"Relevant evidence excerpts:\n{source_lines}"
    )


def method_for_skill(skill: SkillDefinition) -> str:
    haystack = f"{skill.name} {skill.display_name} {skill.description}".lower()
    for key, method in METHOD_HINTS.items():
        if key in haystack:
            return method
    if skill.skill_type == "quantitative":
        return "quantitative UX research analysis with explicit metric interpretation"
    if skill.skill_type == "qualitative":
        return "qualitative UX research analysis with evidence coding"
    return "mixed-methods UX research analysis with Atomic Research evidence chains"


def sample_value(schema: Any, skill: SkillDefinition, key: str = "value", depth: int = 0) -> Any:
    if depth > 6:
        return f"{skill.display_name} {key}"
    if not isinstance(schema, dict):
        return schema

    if "anyOf" in schema:
        non_null = [item for item in schema["anyOf"] if item.get("type") != "null"]
        return sample_value(non_null[0] if non_null else {"type": "string"}, skill, key, depth + 1)

    if "enum" in schema:
        return schema["enum"][0]

    schema_type = schema.get("type", "string")
    if schema_type == "object":
        return {
            prop: sample_value(prop_schema, skill, prop, depth + 1)
            for prop, prop_schema in schema.get("properties", {}).items()
        }
    if schema_type == "array":
        return [
            sample_value(schema.get("items", {"type": "string"}), skill, key.rstrip("s") or "item", depth + 1)
        ]
    if schema_type == "integer":
        return 3
    if schema_type == "number":
        return 4.2
    if schema_type == "boolean":
        return True
    return string_sample(skill, key)


def string_sample(skill: SkillDefinition, key: str) -> str:
    key_lower = key.lower()
    if "nugget" in key_lower or "quote" in key_lower or "evidence" in key_lower:
        return RANDOM.choice(NUGGET_BANK)[0]
    if "source" in key_lower:
        return "Interview_P01"
    if "method" in key_lower:
        return method_for_skill(skill)
    if "recommend" in key_lower:
        return f"Prioritize the highest-evidence {skill.display_name.lower()} opportunity."
    if "summary" in key_lower:
        return f"{skill.display_name} found evidence-backed opportunities across the research corpus."
    if "confidence" in key_lower:
        return "high"
    if "id" in key_lower:
        return f"{skill.name}_1"
    return f"{skill.display_name} {key.replace('_', ' ')}"


def assistant_payload(skill: SkillDefinition) -> str:
    output = sample_value(skill.strict_schema, skill)
    return (
        f"<thinking>\n"
        f"Apply {method_for_skill(skill)}. Extract Nuggets, verify Facts, then synthesize Insights before final JSON.\n"
        f"</thinking>\n"
        f"<research_methodology>\n{method_for_skill(skill)}\n</research_methodology>\n"
        f"{json.dumps(output, ensure_ascii=False, indent=2)}"
    )


def messages_entry(skill: SkillDefinition, variant: int) -> dict[str, Any]:
    context = research_context(skill)
    instruction = (
        f"Run {skill.display_name} using the provided Istara research data. "
        f"Return strict JSON matching the live `{skill.name}` schema."
    )
    if variant == 1:
        instruction = f"Create an evidence-grounded {skill.display_name} deliverable for this Istara project."
    elif variant == 2:
        instruction = f"Use `{skill.name}` to transform the research excerpts into schema-valid output."
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"{instruction}\n\n{context}"},
            {"role": "assistant", "content": assistant_payload(skill)},
        ],
        "tools": [tool_for_skill(skill)],
        "competency": "schema_compliance",
        "skill": skill.name,
        "phase": skill.phase,
        "skill_type": skill.skill_type,
        "source_definition": str(skill.source_path.relative_to(ROOT.parent)),
    }


def alpaca_from_messages(entry: dict[str, Any]) -> dict[str, str]:
    user_content = next(message["content"] for message in entry["messages"] if message["role"] == "user")
    assistant_content = next(message["content"] for message in entry["messages"] if message["role"] == "assistant")
    first_line, _, rest = user_content.partition("\n\n")
    return {"instruction": first_line, "input": rest, "output": assistant_content}


def dag_entry(skills: list[SkillDefinition]) -> dict[str, Any]:
    selected = RANDOM.sample(skills, min(4, len(skills)))
    steps = []
    for index, skill in enumerate(selected, start=1):
        steps.append(
            {
                "id": f"step_{index}",
                "description": f"Run {skill.display_name} for the integrated Istara research workflow.",
                "skill_name": skill.name,
                "depends_on": [] if index == 1 else [f"step_{index - 1}"],
            }
        )
    user_content = "Plan a multi-step Istara research workflow that combines discovery, analysis, and synthesis."
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
            {
                "role": "assistant",
                "content": "<thinking>\nDecompose the request into a DAG of live Istara skills.\n</thinking>\n"
                f"<tool_call>\n{json.dumps({'steps': steps}, indent=2)}\n</tool_call>",
            },
        ],
        "tools": [tool_for_skill(skill) for skill in selected],
        "competency": "tool_invocation_dag",
        "skill": "_create_research_plan",
    }


def anti_pattern_entry(skills: list[SkillDefinition]) -> dict[str, Any]:
    skill_names = ", ".join(skill.name for skill in skills[:8])
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "Can you analyze our UX research?"},
            {
                "role": "assistant",
                "content": (
                    "<thinking>\nThe request is underspecified. Ask for scope, evidence, and intended method.\n</thinking>\n"
                    "I need the research material, objective, and target method before running an Istara skill. "
                    f"Relevant available skills include: {skill_names}."
                ),
            },
        ],
        "tools": [tool_for_skill(skill) for skill in skills[:8]],
        "competency": "anti_pattern_clarification",
        "skill": "clarification",
    }


def atomic_research_entry() -> dict[str, Any]:
    nuggets = RANDOM.sample(NUGGET_BANK, 5)
    facts = [
        {
            "text": "Participants repeatedly struggled with navigation and feature discoverability.",
            "supporting_nuggets": [nuggets[0][0], nuggets[1][0]],
            "source_count": 2,
        }
    ]
    insights = [
        {
            "text": "Navigation uncertainty is reducing confidence during first-use workflows.",
            "confidence": "medium",
            "supporting_facts": [facts[0]["text"]],
        }
    ]
    output = {
        "nuggets": [{"text": text, "source": source, "tags": tags} for text, source, tags in nuggets],
        "facts": facts,
        "insights": insights,
        "recommendations": [
            {
                "text": "Expose primary actions earlier in onboarding and validate them with first-use usability tests.",
                "priority": "high",
                "supporting_insights": [insights[0]["text"]],
            }
        ],
    }
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "Build an Atomic Research chain from these interview observations."},
            {
                "role": "assistant",
                "content": "<thinking>\nMap raw observations to Nuggets, Facts, Insights, and Recommendations.\n</thinking>\n"
                "<research_methodology>\nAtomic Research hierarchy\n</research_methodology>\n"
                f"{json.dumps(output, indent=2)}",
            },
        ],
        "tools": [],
        "competency": "atomic_research",
        "skill": "atomic-research",
    }


def generate_entries(skills: list[SkillDefinition], samples_per_skill: int) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for skill in skills:
        for variant in range(samples_per_skill):
            entries.append(messages_entry(skill, variant))
    for _ in range(max(10, len(skills) // 2)):
        entries.append(dag_entry(skills))
    for _ in range(25):
        entries.append(anti_pattern_entry(skills))
        entries.append(atomic_research_entry())
    RANDOM.shuffle(entries)
    return entries


def validate_entries(entries: list[dict[str, Any]], skills: list[SkillDefinition]) -> dict[str, Any]:
    skill_counts = Counter(entry["skill"] for entry in entries)
    missing = [skill.name for skill in skills if skill_counts[skill.name] == 0]
    if missing:
        raise RuntimeError(f"Generated dataset omitted live skills: {missing}")
    for entry in entries:
        json.dumps(entry)
        alpaca = alpaca_from_messages(entry)
        if set(alpaca) != {"instruction", "input", "output"}:
            raise RuntimeError("Invalid Alpaca record shape")
    return {
        "total_entries": len(entries),
        "live_skill_count": len(skills),
        "competencies": dict(Counter(entry["competency"] for entry in entries)),
        "skills": dict(skill_counts),
        "repo_id": REPO_ID,
        "formats": ["messages+tools", "alpaca_instruction_input_output", "full_metadata"],
    }


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def upload_outputs(paths: list[Path], info_path: Path) -> None:
    try:
        from huggingface_hub import HfApi
    except ImportError as exc:
        raise RuntimeError("Install huggingface_hub to use --upload") from exc

    api = HfApi()
    for path in paths + [info_path]:
        api.upload_file(
            path_or_fileobj=str(path),
            path_in_repo=f"istara_sft/{path.name}",
            repo_id=REPO_ID,
            repo_type="dataset",
            commit_message=f"Update Istara SFT dataset artifact: {path.name}",
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--samples-per-skill", type=int, default=4)
    parser.add_argument("--upload", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    skills = load_skill_definitions()
    if not skills:
        raise RuntimeError(f"No skill definitions found in {SKILLS_DIR}")

    entries = generate_entries(skills, args.samples_per_skill)
    info = validate_entries(entries, skills)

    messages_records = [{"messages": entry["messages"], "tools": entry["tools"]} for entry in entries]
    alpaca_records = [alpaca_from_messages(entry) for entry in entries]

    messages_path = args.out_dir / "istara_sft_messages.jsonl"
    alpaca_path = args.out_dir / "istara_sft_alpaca.jsonl"
    full_path = args.out_dir / "istara_sft_full.jsonl"
    info_path = args.out_dir / "dataset_info.json"

    write_jsonl(messages_path, messages_records)
    write_jsonl(alpaca_path, alpaca_records)
    write_jsonl(full_path, entries)
    info_path.write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")

    print("=== Istara SFT Dataset Generator ===")
    print(f"Loaded live skills: {len(skills)}")
    print(f"Generated entries: {info['total_entries']}")
    print(f"Messages JSONL: {messages_path}")
    print(f"Alpaca JSONL: {alpaca_path}")
    print(f"Full JSONL: {full_path}")
    print(f"Dataset info: {info_path}")

    if args.upload:
        upload_outputs([messages_path, alpaca_path, full_path], info_path)
        print(f"Uploaded to https://huggingface.co/datasets/{REPO_ID}/tree/main/istara_sft")
    else:
        print("Upload skipped. Pass --upload to push artifacts to Hugging Face.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
