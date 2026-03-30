"""Pytest configuration for Istara tests."""

import sys
from pathlib import Path

# Ensure backend is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
