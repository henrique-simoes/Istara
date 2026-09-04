export interface SuggestionStreamEvent {
  type: string;
  content?: string;
  message?: string;
}

export type SuggestionStreamFactory = (
  projectId: string,
  content: string,
  sessionId?: string,
  signal?: AbortSignal,
) => AsyncIterable<SuggestionStreamEvent>;

export function createSuggestionStream(
  send: SuggestionStreamFactory,
  projectId: string,
  content: string,
  sessionId: string | undefined,
  signal: AbortSignal,
): AsyncIterable<SuggestionStreamEvent> {
  return send(projectId, content, sessionId, signal);
}

export async function consumeSuggestionStreamEvents(
  events: AsyncIterable<SuggestionStreamEvent>,
  onChunk: (content: string) => void,
): Promise<void> {
  let accumulated = "";

  for await (const event of events) {
    if (event.type === "chunk" && event.content) {
      accumulated += event.content;
      onChunk(accumulated);
    } else if (event.type === "error") {
      throw new Error(event.message || "Failed to get AI response");
    }
  }
}
