import { describe, expect, it } from "vitest";
import { memorySourceLabel } from "./memorySourceLabels";

describe("memorySourceLabel", () => {
  const documents = [
    {
      title: "Interview Dashboard Usability",
      file_name: "interview-dashboard-usability.md",
      file_path: "data/uploads/project-1/7e8f760a.md",
    },
  ];

  it("resolves a managed upload path to its title and filename", () => {
    expect(memorySourceLabel("data/uploads/project-1/7e8f760a.md", documents))
      .toBe("Interview Dashboard Usability (interview-dashboard-usability.md)");
  });

  it("uses a stable basename when a source is not registered", () => {
    expect(memorySourceLabel("data/uploads/project-1/unregistered.md", documents))
      .toBe("unregistered.md");
  });
});
