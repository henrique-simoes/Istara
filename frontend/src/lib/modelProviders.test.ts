import { afterEach, describe, expect, it, vi } from "vitest";

import { detectLocalLLM, openAIUrl, providerLabel } from "./modelProviders";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("model provider contract helpers", () => {
  it("labels expanded provider types", () => {
    expect(providerLabel("vllm")).toBe("vLLM");
    expect(providerLabel("sglang")).toBe("SGLang");
    expect(providerLabel("anthropic")).toBe("Anthropic");
  });

  it("does not duplicate OpenAI-compatible base paths", () => {
    expect(openAIUrl("https://example.test/v1", "openai_compat", "models")).toBe(
      "https://example.test/v1/models"
    );
    expect(
      openAIUrl(
        "https://generativelanguage.googleapis.com/v1beta/openai",
        "gemini_openai",
        "chat/completions"
      )
    ).toBe("https://generativelanguage.googleapis.com/v1beta/openai/chat/completions");
  });

  it("detects LM Studio native metadata for browser compute donation", async () => {
    const fetchMock = vi.fn(async (url: string) => {
      if (url === "http://localhost:1234/api/v1/models") {
        return new Response(
          JSON.stringify({
            models: [
              {
                key: "qwen3.6-35b-a3b",
                type: "vlm",
                capabilities: { vision: true, trained_for_tool_use: true },
                loaded_instances: [{ config: { context_length: 100000 } }],
              },
            ],
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        );
      }
      throw new Error("unreachable");
    });
    vi.stubGlobal("fetch", fetchMock);

    const detected = await detectLocalLLM();

    expect(detected?.providerType).toBe("lmstudio");
    expect(detected?.models).toEqual(["qwen3.6-35b-a3b"]);
    expect(detected?.modelCapabilities["qwen3.6-35b-a3b"].supports_vision).toBe(true);
    expect(detected?.modelCapabilities["qwen3.6-35b-a3b"].loaded_context_length).toBe(100000);
  });
});
