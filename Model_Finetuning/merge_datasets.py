import json
from pathlib import Path
from cleaned_nuggets import NUGGET_BANK

def main():
    root = Path(__file__).parent
    qual = root / "qualitative_nuggets.json"
    quant = root / "quantitative_nuggets.json"
    rtf = root / "rtf_nuggets.json"
    
    merged = list(NUGGET_BANK)
    seen = {str(n[0]) for n in merged}
    
    for p in [qual, quant, rtf]:
        if p.exists():
            data = json.loads(p.read_text())
            for n in data:
                text = str(n[0])
                source = str(n[1])
                tags = list(n[2])
                if text not in seen:
                    merged.append((text, source, tags))
                    seen.add(text)
                    
    out_file = root / "consolidated_bank.py"
    with out_file.open("w", encoding="utf-8") as f:
        f.write("NUGGET_BANK = [\n")
        for item in merged:
            f.write(f"    {repr(tuple(item))},\n")
        f.write("]\n")
        
    print(f"Merged total {len(merged)} nuggets into consolidated_bank.py")

if __name__ == "__main__":
    main()
