import json
import csv
from pathlib import Path

ROOT = Path(__file__).parent / "Qualitative-Text-Datasets-for-UX-Research-main" / "datasets"
TEXT_KEYS = {
    "response_text",
    "description",
    "text",
    "body",
    "comment",
    "feedback",
    "quote",
    "transcript",
    "observation",
    "summary",
}
NOISE_KEYS = {
    "metadata",
    "date",
    "timestamp",
    "user_id",
    "participant_id",
    "ticket_id",
    "response_id",
    "status",
    "priority",
    "category",
    "urgency",
}


def _looks_useful_text(value: str) -> bool:
    value = value.strip()
    return len(value) >= 30 and any(char.isalpha() for char in value)


def _walk_json(value, source, method_tag, nuggets, key=""):
    if isinstance(value, dict):
        for child_key, child_value in value.items():
            lower = child_key.lower()
            if lower in NOISE_KEYS or lower.endswith("_metadata"):
                continue
            _walk_json(child_value, source, method_tag, nuggets, lower)
        return

    if isinstance(value, list):
        for item in value:
            _walk_json(item, source, method_tag, nuggets, key)
        return

    if isinstance(value, str) and _looks_useful_text(value):
        if key in TEXT_KEYS or len(value) >= 80:
            nuggets.append((value.strip(), source, [method_tag, "qualitative"]))

def process():
    nuggets = []
    if not ROOT.exists():
        print(f"Directory {ROOT} not found.")
        return
    for path in ROOT.rglob("*"):
        if path.is_file():
            method_tag = path.parent.name
            source = path.name
            if path.suffix == ".json":
                try:
                    data = json.loads(path.read_text())
                    _walk_json(data, source, method_tag, nuggets)
                except Exception as e:
                    print(f"Failed to parse {path}: {e}")
            elif path.suffix == ".csv":
                try:
                    with path.open(encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            for key, value in row.items():
                                if key and key.lower() in TEXT_KEYS and value and _looks_useful_text(value):
                                    nuggets.append((value.strip(), source, [method_tag, "qualitative"]))
                except Exception as e:
                    print(f"Failed to parse {path}: {e}")
            elif path.suffix in [".txt", ".md"]:
                try:
                    text = path.read_text(encoding="utf-8")
                    blocks = text.split("\n\n")
                    for block in blocks:
                        if _looks_useful_text(block) and not block.startswith("==="):
                            nuggets.append((block.strip(), source, [method_tag, "qualitative"]))
                except Exception as e:
                    print(f"Failed to parse {path}: {e}")
    
    out = Path(__file__).parent / "qualitative_nuggets.json"
    out.write_text(json.dumps(nuggets, indent=2))
    print(f"Qualitative adapter extracted {len(nuggets)} nuggets.")

if __name__ == "__main__":
    process()
