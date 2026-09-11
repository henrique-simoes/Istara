from pathlib import Path

from scripts.verify_control_plane_triage import verify


# CI runs pytest with working-directory: backend, so repo-relative data paths
# must be resolved from this file's location, never from the process CWD.
REPO_ROOT = Path(__file__).resolve().parents[1]
TRIAGE = REPO_ROOT / "docs/promotion/2026-09-09-control-plane-triage.tsv"
REVIEW = "testing-to-main-20260909-WAVE-control-plane-lifecycle-REVIEW"


def test_tracked_triage_preserves_current_promotion_prerequisites() -> None:
    assert verify(
        TRIAGE,
        spec="CF-SPEC-30",
        pipeline_run="testing-to-main-20260909",
        current_review=REVIEW,
    ) == []


def test_blanket_non_blocking_label_is_rejected(tmp_path: Path) -> None:
    text = TRIAGE.read_text(encoding="utf-8")
    text = text.replace("acceptance-prerequisite", "open-not-release-blocking")
    text = text.replace("promotion-prerequisite", "open-not-release-blocking")
    altered = tmp_path / "triage.tsv"
    altered.write_text(text, encoding="utf-8")

    errors = verify(
        altered,
        spec="CF-SPEC-30",
        pipeline_run="testing-to-main-20260909",
        current_review=REVIEW,
    )
    assert len(errors) == 10
    assert all("prerequisite" in error for error in errors)
