import { describe, expect, it } from "vitest";

import {
  consumeSuggestionStreamEvents,
  createSuggestionStream,
} from "./suggestionStream";

async function* events(
  values: Array<{ type: string; content?: string; message?: string }>,
) {
  for (const value of values) yield value;
}

describe("interactive suggestion streams", () => {
  it("rejects with the server-provided message when SSE returns an error event", async () => {
    const chunks: string[] = [];

    await expect(
      consumeSuggestionStreamEvents(
        events([
          {
            type: "error",
            message: "No chat-ready model is configured. Choose one in Settings.",
          },
        ]),
        (content) => chunks.push(content),
      ),
    ).rejects.toThrow("No chat-ready model is configured. Choose one in Settings.");
    expect(chunks).toEqual([]);
  });

  it("accumulates chunk events in display order", async () => {
    const chunks: string[] = [];

    await consumeSuggestionStreamEvents(
      events([
        { type: "chunk", content: "Organize" },
        { type: "usage" },
        { type: "chunk", content: " by phase." },
        { type: "done" },
      ]),
      (content) => chunks.push(content),
    );

    expect(chunks).toEqual(["Organize", "Organize by phase."]);
  });

  it("forwards the active AbortSignal to the chat request", async () => {
    const controller = new AbortController();
    let receivedSignal: AbortSignal | undefined;
    const send = (
      _projectId: string,
      _content: string,
      _sessionId: string | undefined,
      signal?: AbortSignal,
    ) => {
      receivedSignal = signal;
      return events([]);
    };

    const stream = createSuggestionStream(
      send,
      "project-1",
      "organize",
      "session-1",
      controller.signal,
    );
    await consumeSuggestionStreamEvents(stream, () => undefined);

    expect(receivedSignal).toBe(controller.signal);
  });
});
