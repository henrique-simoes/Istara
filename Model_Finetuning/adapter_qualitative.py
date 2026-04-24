import json
import csv
from pathlib import Path

ROOT = Path(__file__).parent / "Qualitative-Text-Datasets-for-UX-Research-main" / "datasets"

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
                    for iv in data.get("interviews", []):
                        responses = iv.get("responses", {})
                        if isinstance(responses, dict):
                            for k, v in responses.items():
                                nuggets.append((str(v), source, [method_tag, "qualitative"]))
                        elif isinstance(responses, str):
                            nuggets.append((responses, source, [method_tag, "qualitative"]))
                except Exception:
                    pass
            elif path.suffix == ".csv":
                try:
                    with path.open(encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            if "response_text" in row:
                                nuggets.append((row["response_text"], source, [method_tag, "qualitative"]))
                except Exception:
                    pass
            elif path.suffix in [".txt", ".md"]:
                try:
                    text = path.read_text(encoding="utf-8")
                    blocks = text.split("\n\n")
                    for block in blocks:
                        if block.strip() and not block.startswith("==="):
                            nuggets.append((block.strip(), source, [method_tag, "qualitative"]))
                except Exception:
                    pass
    
    out = Path(__file__).parent / "qualitative_nuggets.json"
    out.write_text(json.dumps(nuggets, indent=2))
    print(f"Qualitative adapter extracted {len(nuggets)} nuggets.")

if __name__ == "__main__":
    process()
