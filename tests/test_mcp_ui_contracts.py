"""Static contracts for the MCP registration form's fail-closed validation."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_mcp_registration_form_blocks_malformed_urls_before_network_actions() -> None:
    setup = (ROOT / "frontend/src/components/integrations/MCPServerSetup.tsx").read_text()

    assert 'isValidMcpServerUrl, mcpServerUrlError } from "@/lib/mcpUrl";' in setup
    assert "const urlValid = isValidMcpServerUrl(url);" in setup
    assert "disabled={!urlValid || !projectId || testing}" in setup
    assert "disabled={!urlValid || !projectId || saving}" in setup
    assert 'role="alert"' in setup
    assert "mcpServerUrlError(url)" in setup
