import { describe, expect, it, vi } from "vitest";

import {
  loadTaskDocumentReferences,
  resolveTaskDocumentTitle,
} from "./taskDocumentTitles";

describe("task document title resolution", () => {
  it("fetches attached documents that are outside the picker page", async () => {
    const api = {
      list: vi.fn().mockResolvedValue({
        documents: [{ id: "known", title: "Known interview" }],
      }),
      get: vi.fn().mockResolvedValue({ id: "missing", title: "Older interview" }),
    };

    const documents = await loadTaskDocumentReferences(api, "project-1", ["known", "missing"]);

    expect(api.list).toHaveBeenCalledWith({ project_id: "project-1", page_size: 100 });
    expect(api.get).toHaveBeenCalledWith("missing", "project-1");
    expect(documents).toEqual([
      { id: "known", title: "Known interview" },
      { id: "missing", title: "Older interview" },
    ]);
  });

  it("never falls back to an identifying UUID fragment", () => {
    expect(resolveTaskDocumentTitle([], "uuid-123456789", false)).toBe("Document unavailable");
    expect(resolveTaskDocumentTitle([], "uuid-123456789", true)).toBe("Loading document title…");
    expect(resolveTaskDocumentTitle([{ id: "doc-1", title: "  Interview P1  " }], "doc-1", false)).toBe(
      "Interview P1",
    );
  });
});
