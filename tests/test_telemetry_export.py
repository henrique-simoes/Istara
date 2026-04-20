"""Tests for telemetry export — local JSON export without phone-home."""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_mock_result(scalars_return):
    mock_scalars = MagicMock()
    mock_scalars.all = MagicMock(return_value=scalars_return)
    mock_result = MagicMock()
    mock_result.scalars = MagicMock(return_value=mock_scalars)
    return mock_result


async def _mock_execute_factory(scalars_return):
    return _make_mock_result(scalars_return)


class TestTelemetryExport:
    @pytest.mark.asyncio
    async def test_export_telemetry_includes_models_creates_models_file(self):
        import importlib
        from app.core import telemetry_export as te_module

        importlib.reload(te_module)

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=[])
        mock_result.scalars = MagicMock(return_value=mock_scalars)

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock(return_value=None)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        def make_session():
            return mock_session

        export_dir = Path("/tmp/istara_export_test")
        export_dir.mkdir(parents=True, exist_ok=True)
        try:
            with patch.object(te_module, "async_session", make_session):
                with patch.object(
                    te_module.settings, "telemetry_export_dir", str(export_dir)
                ):
                    result = await te_module.export_telemetry(
                        project_id="proj-test", days=7, include_models=True
                    )
                    assert "model_stats_count" in result, f"Keys: {list(result.keys())}"
                    assert "models_file" in result
                    assert result["model_stats_count"] == 0
        finally:
            import shutil

            shutil.rmtree(export_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_export_telemetry_respects_days_parameter(self):
        from app.core.telemetry_export import export_telemetry

        with tempfile.TemporaryDirectory() as tmp:
            with patch("app.core.telemetry_export.settings") as mock_settings:
                mock_settings.telemetry_export_dir = tmp
                with patch("app.core.telemetry_export.async_session") as mock_session:
                    mock_ctx = AsyncMock()
                    mock_session.return_value.__aenter__ = AsyncMock(
                        return_value=mock_ctx
                    )
                    mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
                    mock_ctx.execute = AsyncMock(return_value=_make_mock_result([]))

                    result = await export_telemetry(project_id="proj-test", days=30)

                    assert result["days"] == 30
                    summary = json.loads(Path(result["files"]["summary"]).read_text())
                    assert summary["days"] == 30

    @pytest.mark.asyncio
    async def test_export_filename_includes_project_tag(self):
        from app.core.telemetry_export import export_telemetry

        with tempfile.TemporaryDirectory() as tmp:
            with patch("app.core.telemetry_export.settings") as mock_settings:
                mock_settings.telemetry_export_dir = tmp
                with patch("app.core.telemetry_export.async_session") as mock_session:
                    mock_ctx = AsyncMock()
                    mock_session.return_value.__aenter__ = AsyncMock(
                        return_value=mock_ctx
                    )
                    mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
                    mock_ctx.execute = AsyncMock(return_value=_make_mock_result([]))

                    await export_telemetry(
                        project_id="my-project", days=1, include_models=False
                    )

                    summary_files = list(
                        Path(tmp).glob("istara_telemetry_my-project_*_summary.json")
                    )
                    assert len(summary_files) == 1
