import { describe, expect, it } from "vitest";

import { primaryNavItemsForRole } from "./navigation";

describe("primary navigation role filtering", () => {
  it("hides researcher-only Loops from viewers while retaining the core views", () => {
    const viewerIds = primaryNavItemsForRole("viewer").map((item) => item.id);

    expect(viewerIds).not.toContain("loops");
    expect(viewerIds).toContain("chat");
    expect(viewerIds).toContain("settings");
  });

  it("keeps Loops available to researcher and admin roles", () => {
    expect(primaryNavItemsForRole("researcher").map((item) => item.id)).toContain("loops");
    expect(primaryNavItemsForRole("admin").map((item) => item.id)).toContain("loops");
  });
});
