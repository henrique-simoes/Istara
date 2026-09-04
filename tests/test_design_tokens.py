"""Design-token determinism gate (DESIGN.md governance).

docs/design/tokens.json must always equal what scripts/export_design_tokens.py
derives from globals.css + tailwind.config.js. Hand-editing the JSON fails here.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_exported_design_tokens_match_sources():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "export_design_tokens.py"), "--check"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"design tokens drifted:\n{result.stdout}\n{result.stderr}"
    )
