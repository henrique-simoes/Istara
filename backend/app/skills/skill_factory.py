"""Skill factory — generate skills from configuration to reduce boilerplate.

Each skill has the same core pattern:
1. plan() — generate a research plan using LLM
2. execute() — process input files + context, extract findings using LLM
3. validate_output() — check quality

This factory creates concrete skill classes from config dicts.
"""

import json
import re
from pathlib import Path
from typing import Any

from app.core.ollama import ollama
from app.core.file_processor import process_file
from app.skills.base import BaseSkill, SkillInput, SkillOutput, SkillPhase, SkillType


def _make_schema_strict(schema: Any) -> dict:
    """Transform JSON Schema (or example object) to strict mode for local LLMs.
    
    If the input is already a JSON Schema (has 'type'), it adds 'additionalProperties': False
    and 'required' arrays to every object.
    
    If the input is an example object (e.g. {"key": "value"}), it recursively 
    translates it into a valid JSON Schema with strict constraints.
    """
    if not isinstance(schema, (dict, list)):
        # Base case: map python type to JSON schema type
        if isinstance(schema, bool):
            return {"type": "boolean"}
        if isinstance(schema, int):
            return {"type": "integer"}
        if isinstance(schema, float):
            return {"type": "number"}
        return {"type": "string"}

    if isinstance(schema, list):
        # Example array or Schema array
        if len(schema) > 0 and isinstance(schema[0], dict) and "type" in schema[0]:
            # It's a schema array
            return {
                "type": "array",
                "items": _make_schema_strict(schema[0])
            }
        else:
            # It's an example array
            item_example = schema[0] if len(schema) > 0 else "..."
            return {
                "type": "array",
                "items": _make_schema_strict(item_example)
            }

    if isinstance(schema, dict):
        # Check if it's already a JSON Schema
        if "type" in schema:
            new_schema = schema.copy()
            if new_schema["type"] == "object":
                new_schema["additionalProperties"] = False
                properties = new_schema.get("properties", {})
                required = new_schema.get("required", [])
                
                new_required = list(properties.keys())
                new_properties = {}
                
                for prop_name, prop_schema in properties.items():
                    prop_schema_strict = _make_schema_strict(prop_schema)
                    # Handle optional fields (if they weren't in the original required list)
                    if prop_name not in required:
                        if "type" in prop_schema_strict and isinstance(prop_schema_strict["type"], str):
                            original_type = prop_schema_strict.pop("type")
                            prop_schema_strict["anyOf"] = [{"type": original_type}, {"type": "null"}]
                    new_properties[prop_name] = prop_schema_strict
                
                new_schema["properties"] = new_properties
                new_schema["required"] = new_required
            elif new_schema["type"] == "array":
                if "items" in new_schema:
                    new_schema["items"] = _make_schema_strict(new_schema["items"])
            return new_schema
        
        # It's an example object — translate to Schema
        new_properties = {}
        new_required = []
        for k, v in schema.items():
            new_properties[k] = _make_schema_strict(v)
            new_required.append(k)
            
        return {
            "type": "object",
            "properties": new_properties,
            "required": new_required,
            "additionalProperties": False
        }
    
    return {"type": "string"}


def _extract_text_from_files(files: list[str], max_chars: int = 4000) -> str:
    """Extract text from input files."""
    texts = []
    total = 0
    for f in files:
        result = process_file(Path(f))
        if not result.error and result.chunks:
            for chunk in result.chunks:
                if total + len(chunk.text) > max_chars:
                    break
                texts.append(chunk.text)
                total += len(chunk.text)
    return "\n\n".join(texts)


def _parse_json_response(text: str) -> dict:
    """Try to extract JSON from an LLM response."""
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except (json.JSONDecodeError, ValueError):
        pass
    return {}


def create_skill(
    skill_name: str,
    display: str,
    desc: str,
    phase: SkillPhase,
    skill_type: SkillType,
    plan_prompt: str,
    execute_prompt: str,
    output_schema: str,
) -> type[BaseSkill]:
    """Create a concrete skill class from configuration.

    Args:
        skill_name: Unique identifier (e.g., 'competitive-analysis')
        display: Human name (e.g., 'Competitive Analysis')
        desc: Description of what the skill does
        phase: Double Diamond phase
        skill_type: Qual/quant/mixed
        plan_prompt: Prompt template for plan(). Uses {context}, {user_context}
        execute_prompt: Prompt template for execute(). Uses {context}, {content}
        output_schema: JSON schema description appended to execute_prompt
    """

    class GeneratedSkill(BaseSkill):
        @property
        def name(self) -> str:
            return skill_name

        @property
        def display_name(self) -> str:
            return display

        @property
        def description(self) -> str:
            return desc

        @property
        def phase(self) -> SkillPhase:
            return phase

        @property
        def skill_type(self) -> SkillType:
            return skill_type

        async def plan(self, skill_input: SkillInput) -> dict:
            ctx = skill_input.project_context or skill_input.user_context or "General UX research"
            urls_str = ", ".join(skill_input.urls) if skill_input.urls else ""
            prompt = plan_prompt.format(
                context=ctx, user_context=skill_input.user_context or "", urls=urls_str
            )
            resp = await ollama.chat(
                messages=[{"role": "user", "content": prompt}], temperature=0.7
            )
            return {"skill": self.name, "plan": resp.get("message", {}).get("content", "")}

        async def execute(self, skill_input: SkillInput) -> SkillOutput:
            content = _extract_text_from_files(skill_input.files) if skill_input.files else ""
            if not content and not skill_input.user_context and not skill_input.urls:
                return SkillOutput(
                    success=False,
                    summary="No input provided.",
                    errors=["Provide files, context, or URLs."],
                )

            file_sources = [Path(f).name for f in skill_input.files] if skill_input.files else []
            source_label = ", ".join(file_sources[:3]) if file_sources else self.name

            ctx = "\n".join(
                filter(
                    None,
                    [
                        skill_input.company_context,
                        skill_input.project_context,
                        skill_input.user_context,
                    ],
                )
            )
            data_content = content or (skill_input.user_context or "N/A")[:10000]

            # SOTA Prompt Construction (Anthropic/OpenAI hybrid)
            full_prompt = (
                f"<skill_context>\n"
                f"Name: {self.name}\n"
                f"Description: {self.description}\n"
                f"Phase: {self.phase.value}\n"
                f"</skill_context>\n\n"
                f"<research_methodology>\n"
                f"{execute_prompt.format(context=(ctx or 'N/A')[:2000], content='[RESEARCH_DATA_BELOW]', urls=', '.join(skill_input.urls) if skill_input.urls else '', urls_section='')}\n"
                f"</research_methodology>\n\n"
                f"<research_data>\n"
                f"{data_content}\n"
                f"</research_data>\n\n"
                f"<instructions>\n"
                f"1. **Think First**: Analyze the research data against the methodology inside <thinking> tags.\n"
                f"2. **Extract Evidence**: Find exact nuggets (quotes) with source tracking.\n"
                f"3. **Synthesize**: Move from nuggets to facts, then to high-level insights.\n"
                f"4. **Format**: Respond with a valid JSON object matching the schema below.\n"
                f"</instructions>\n\n"
                f"## Output Schema\n"
                f"{output_schema}"
            )

            # Try to parse schema as dict for native support
            schema_dict = None
            try:
                parsed_schema = json.loads(output_schema)
                strict_schema = _make_schema_strict(parsed_schema)
                schema_dict = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": f"{self.name.replace('-', '_')}_output",
                        "schema": strict_schema,
                        "strict": True
                    }
                }
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Skill {self.name} failed to prepare strict schema: {e}")

            resp = await ollama.chat(
                messages=[{"role": "user", "content": full_prompt}], 
                temperature=0.2, # Lower temperature for analytical rigor
                response_format=schema_dict, # Enable native structured outputs
                system="You are a meticulous UX Research Auditor. You prioritize evidence over assumption."
            )
            
            raw_content = resp.get("message", {}).get("content", "")
            
            # Remove thinking tags from JSON parsing if model included them outside JSON
            clean_content = re.sub(r"<thinking>.*?</thinking>", "", raw_content, flags=re.DOTALL).strip()
            
            json_success = False
            try:
                data = _parse_json_response(clean_content)
                json_success = True
            except Exception as e:
                logger.warning(f"Skill {self.name} failed to parse JSON: {e}")
                data = {}
            
            # Attach json_success to output for telemetry via hooks
            # (Note: SkillOutput doesn't have json_success, so we use metadata if available or rely on context in orchestrator)

            # Normalize findings — handle both dict and string items from LLM
            def _as_dict(item, default_key="text"):
                return item if isinstance(item, dict) else {default_key: str(item)}

            # Use source from LLM if provided, fall back to file name(s), then skill name
            nuggets = [
                {
                    "text": _as_dict(n).get("text", str(n)),
                    "source": _as_dict(n).get("source", source_label),
                    "tags": _as_dict(n).get("tags", []),
                }
                for n in data.get("nuggets", [])
            ]
            facts = [{"text": _as_dict(f).get("text", str(f))} for f in data.get("facts", [])]
            insights = [
                {
                    "text": _as_dict(i).get("text", str(i)),
                    "confidence": _as_dict(i).get("confidence", "medium"),
                }
                for i in data.get("insights", [])
            ]
            recommendations = [
                {
                    "text": _as_dict(r).get("text", str(r)),
                    "priority": _as_dict(r).get("priority", "medium"),
                }
                for r in data.get("recommendations", [])
            ]

            out = SkillOutput(
                success=True,
                summary=data.get("summary", f"Completed {display} analysis."),
                nuggets=nuggets,
                facts=facts,
                insights=insights,
                recommendations=recommendations,
                artifacts={f"{skill_name}_analysis.json": json.dumps(data, indent=2)},
                suggestions=data.get("suggestions", []),
            )
            # Set json_success manually since __init__ may fail in some environments
            out.json_success = json_success
            return out

    # Set a unique class name for debugging
    GeneratedSkill.__name__ = f"{display.replace(' ', '')}Skill"
    GeneratedSkill.__qualname__ = GeneratedSkill.__name__
    return GeneratedSkill
