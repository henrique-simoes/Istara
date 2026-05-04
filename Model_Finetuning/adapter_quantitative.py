import csv
from pathlib import Path
import json

ROOT = Path(__file__).parent / "UX_datasets-main" / "datasets_by_type"


def process():
    nuggets = []
    if not ROOT.exists():
        raise FileNotFoundError(f"Directory {ROOT} not found.")
    for path in ROOT.rglob("*.csv"):
        method_tag = path.parent.name
        source = path.name
        try:
            with path.open(encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    parts = []
                    for k, v in row.items():
                        if v and str(v).strip() and k:
                            parts.append(f"{k}: {str(v).strip()}")
                    if parts:
                        text = " | ".join(parts)
                        nuggets.append((text, source, [method_tag, "quantitative"]))
        except Exception as e:
            print(f"Failed to parse {path}: {e}")

    if not nuggets:
        raise RuntimeError("Quantitative adapter extracted 0 nuggets; check CSV sources.")

    out = Path(__file__).parent / "quantitative_nuggets.json"
    out.write_text(json.dumps(nuggets, indent=2))
    print(f"Quantitative adapter extracted {len(nuggets)} nuggets.")

if __name__ == "__main__":
    process()
