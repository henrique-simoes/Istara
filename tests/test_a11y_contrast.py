"""CF-SPEC-1 ITEM-005: the Agentic Core chooser must pass the WCAG contrast audit.

The audit script composites every alpha-modified token over its real parent
chain and measures light + dark modes against DESIGN.md's bar (4.5:1 text,
3:1 UI boundaries/state/focus). Any palette or class drift that breaks
contrast fails this test.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_agentic_core_chooser_passes_wcag_contrast_audit():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_a11y_contrast.py")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"contrast audit failed:\n{result.stdout}\n{result.stderr}"
