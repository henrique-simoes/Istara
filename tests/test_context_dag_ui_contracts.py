"""Source-level contracts for the Context DAG user interface."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_context_history_search_count_preserves_spacing_before_for() -> None:
    source = (REPO_ROOT / "frontend/src/components/memory/ContextDAGView.tsx").read_text(
        encoding="utf-8"
    )

    # React does not preserve whitespace between adjacent JSX expressions and
    # text nodes, so the separator must be explicit in the rendered label.
    assert '{" "}for &quot;' in source
