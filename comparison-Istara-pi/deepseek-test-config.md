# DeepSeek Test Configuration

Status: approved for the next durable OpenClaw job
Date: 2026-07-19

## Provider

- Provider: DeepSeek.
- Base URL: `https://api.deepseek.com`.
- Model: `deepseek-v4-pro`.
- Runtime secret env var: `DEEPSEEK_API_KEY`.
- Reasoning effort: `high`.
- Thinking: enabled where the client/provider surface supports it.
- Local models: not allowed.

## Secret Rule

Do not write the literal API key to this folder, git-tracked files, JSONL traces, logs,
manifests, article drafts, or OpenClaw status messages.

Allowed to record:

- Env var name: `DEEPSEEK_API_KEY`.
- Boolean availability: `deepseek_key_present`.
- Provider/model/base URL.
- Token usage and cost totals.

Not allowed to record:

- API key value.
- Full request headers.
- Full uncapped prompts/outputs containing private data.
- Secret-bearing shell commands.

## Istara Adapter Expectation

For Istara baseline runs, adapt model management through the existing OpenAI-compatible
client path without changing Istara source code. The runtime request shape should match:

```python
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)

response = client.chat.completions.create(
    model="deepseek-v4-pro",
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello"},
    ],
    stream=False,
    reasoning_effort="high",
    extra_body={"thinking": {"type": "enabled"}},
)
```

## Pi Adapter Expectation

For Pi runs, use Pi's provider/model system where possible. The lab should verify whether
`@earendil-works/pi-ai` already supports DeepSeek configuration for `deepseek-v4-pro`.

If Pi needs a custom/provider override, prefer a local lab adapter configuration rather than
modifying Istara code or vendoring Pi source. Record the adapter mode and exact package
version in `manifest.json`.

## Smoke Before Scale

Before any paired benchmark:

1. Check `DEEPSEEK_API_KEY` exists at runtime without printing it.
2. Run one minimal no-sensitive-content call against DeepSeek through the Istara-compatible
   OpenAI client shape.
3. Run one minimal Pi provider/model smoke if Pi supports the configured DeepSeek path.
4. Record only token usage, latency, model id, and pass/fail.
5. Ask the owner before scaling to a larger paid run if no budget cap is documented.
