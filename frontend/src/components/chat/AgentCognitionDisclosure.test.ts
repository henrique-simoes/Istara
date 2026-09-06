import { describe, expect, it } from "vitest";
import { extractCognitionFromContent } from "./AgentCognitionDisclosure";

describe("extractCognitionFromContent", () => {
  it("extracts <think> blocks and returns clean conversational text", () => {
    const raw = "<think>\nLet me analyze the customer feedback.\nKey pattern found.\n</think>\nHere is the summary of the customer feedback: Users love the feature.";
    const result = extractCognitionFromContent(raw);

    expect(result.cleanContent).toBe("Here is the summary of the customer feedback: Users love the feature.");
    expect(result.thoughts).toHaveLength(1);
    expect(result.thoughts[0]).toContain("Let me analyze the customer feedback.");
    expect(result.toolCalls).toHaveLength(0);
  });

  it("extracts legacy tool output blocks and isolates them from prose", () => {
    const raw = "**search_documents**: {\"results\": [\"doc1\", \"doc2\"]}\n\nBased on the documents, here are the key insights.";
    const result = extractCognitionFromContent(raw);

    expect(result.cleanContent).toBe("Based on the documents, here are the key insights.");
    expect(result.toolCalls).toHaveLength(1);
    expect(result.toolCalls[0].tool).toBe("search_documents");
    expect(result.toolCalls[0].result).toContain("doc1");
  });

  it("extracts both thinking and tools when present", () => {
    const raw = "<think>Checking interviews</think>\n**search_interviews**: {\"count\": 3}\n\nWe found 3 matching interviews.";
    const result = extractCognitionFromContent(raw);

    expect(result.cleanContent).toBe("We found 3 matching interviews.");
    expect(result.thoughts).toHaveLength(1);
    expect(result.thoughts[0]).toBe("Checking interviews");
    expect(result.toolCalls).toHaveLength(1);
    expect(result.toolCalls[0].tool).toBe("search_interviews");
  });

  it("leaves standard markdown prose untouched when no thinking or tool calls exist", () => {
    const raw = "Hello! How can I help with your qualitative research today?";
    const result = extractCognitionFromContent(raw);

    expect(result.cleanContent).toBe(raw);
    expect(result.thoughts).toHaveLength(0);
    expect(result.toolCalls).toHaveLength(0);
  });
});
