import subprocess
from pathlib import Path
import json

def process():
    path = Path(__file__).parent / "Quant_UX_Research_Examples.rtf"
    nuggets = []
    if path.exists():
        try:
            result = subprocess.run(["textutil", "-convert", "txt", str(path), "-stdout"], capture_output=True, text=True)
            text = result.stdout
            blocks = text.split("\n\n")
            for block in blocks:
                block = block.strip()
                if block and (block.startswith("({") or block.startswith("`({")):
                    nuggets.append((block, "Quant_UX_Research_Examples.rtf", ["quantitative_examples", "methodology"]))
        except Exception as e:
            print("RTF extraction failed:", e)
            
    out = Path(__file__).parent / "rtf_nuggets.json"
    out.write_text(json.dumps(nuggets, indent=2))
    print(f"RTF adapter extracted {len(nuggets)} nuggets.")

if __name__ == "__main__":
    process()
