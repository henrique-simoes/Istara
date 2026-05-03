<!-- compass-forge:start -->
# Compass Forge Agent Workflow

Compass Forge is the control plane for this repository.

- Project root: `/Users/user/Documents/Istara-main`
- Recipe: `istararustgraphtrial`
- MCP server: `python -m compass_forge.cli --workspace /Users/user/Documents/compass-forge mcp --target /Users/user/Documents/Istara-main --recipe istararustgraphtrial`

Before editing, run `compass-forge status` and `compass-forge agent-brief --request "<user request>"`.
Use `compass-forge intelligence impact --request "<user request>"` or `--path <path>` before touching important files.
If tasks exist, use `compass-forge work-order --role implementer --task CF-N`.
Run `compass-forge gate before` and `compass-forge gate after` for meaningful changes.
Attach command, gate, and review evidence before marking tasks done.
Do not silently mutate external repos, global agent config, or generated integration files.
<!-- compass-forge:end -->
