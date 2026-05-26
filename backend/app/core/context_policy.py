"""Context Policy — defines protected structures for context management.

Ensures that critical instructions, methodologies, and thinking blocks
remain intact during prompt compression (LLMLingua) or RAG augmentation.
"""

from typing import List

# XML tags that must NEVER be removed or compressed by LLMLingua
PROTECTED_TAGS = [
    "<skill_context>",
    "</skill_context>",
    "<research_methodology>",
    "</research_methodology>",
    "<instructions>",
    "</instructions>",
    "<thinking>",
    "</thinking>",
    "<research_data>",
    "</research_data>",
    "<tool_output>",
    "</tool_output>",
    "<qualitative_coding_protocol>",
    "</qualitative_coding_protocol>",
    "<codebook>",
    "</codebook>",
    "<evidence_units>",
    "</evidence_units>",
    "<coding_matrix>",
    "</coding_matrix>",
    "<reliability_policy>",
    "</reliability_policy>",
    "<promotion_gate>",
    "</promotion_gate>",
    "<route_evidence>",
    "</route_evidence>",
    "<evidence_graph>",
    "</evidence_graph>",
    "<authorization_policy>",
    "</authorization_policy>",
]

# Keywords that signal high-importance instructions
CRITICAL_INSTRUCTIONS = [
    "Braun & Clarke",
    "Nielsen",
    "Fleiss",
    "JTBD",
    "Atomic Research",
    "MoSCoW",
    "JSON",
    "schema",
    "qualitative coding protocol",
    "evidence unit",
    "codebook version",
    "inclusion criteria",
    "exclusion criteria",
    "Cohen",
    "Krippendorff",
    "promotion gate",
    "route evidence",
    "GraphRAG",
    "Hybrid RAG",
    "Done tasks",
]

def is_protected(text: str) -> bool:
    """Check if a string contains any protected tags."""
    return any(tag in text for tag in PROTECTED_TAGS)

def get_protected_blocks(text: str) -> List[tuple[int, int, str]]:
    """Extract start, end indices and content of protected XML blocks."""
    import re
    blocks = []
    # Match any content between protected opening and closing tags
    for i in range(0, len(PROTECTED_TAGS), 2):
        open_tag = PROTECTED_TAGS[i]
        close_tag = PROTECTED_TAGS[i+1]
        pattern = f"{re.escape(open_tag)}.*?{re.escape(close_tag)}"
        for match in re.finditer(pattern, text, re.DOTALL):
            blocks.append((match.start(), match.end(), match.group()))
    return sorted(blocks, key=lambda x: x[0])
