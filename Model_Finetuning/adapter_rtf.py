import re
import shutil
import subprocess
from pathlib import Path
import json


def _rtf_to_text(raw: str) -> str:
    raw = re.sub(r"\\'[0-9a-fA-F]{2}", " ", raw)
    raw = re.sub(r"\\[a-zA-Z]+-?\d* ?", " ", raw)
    raw = raw.replace("\\{", "{").replace("\\}", "}").replace("\\\\", "\\")
    raw = raw.replace("{", " ").replace("}", " ")
    raw = re.sub(r"\s+", " ", raw)
    return raw.strip()


def process():
    path = Path(__file__).parent / "Quant_UX_Research_Examples.rtf"
    nuggets = []
    if path.exists():
        if shutil.which("textutil"):
            result = subprocess.run(
                ["textutil", "-convert", "txt", str(path), "-stdout"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                raise RuntimeError(f"textutil failed: {result.stderr.strip()}")
            text = result.stdout
        else:
            text = _rtf_to_text(path.read_text(encoding="utf-8", errors="ignore"))

        blocks = re.split(r"\n\s*\n|(?=\(\{)|(?=`\(\{)", text)
        for block in blocks:
            block = block.strip().strip("`")
            if block and (block.startswith("({") or block.startswith("{")):
                nuggets.append((block, "Quant_UX_Research_Examples.rtf", ["quantitative_examples", "methodology"]))

    if not nuggets:
        raise RuntimeError("RTF adapter extracted 0 nuggets; check RTF parser and input format.")
            
    out = Path(__file__).parent / "rtf_nuggets.json"
    out.write_text(json.dumps(nuggets, indent=2))
    print(f"RTF adapter extracted {len(nuggets)} nuggets.")

if __name__ == "__main__":
    process()
