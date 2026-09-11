import { describe, expect, it } from "vitest";

import {
  isMobileMoreView,
  isViewAllowed,
  mobileMoreItemsForRole,
  mobilePrimaryItemsForRole,
  primaryNavItemsForRole,
} from "./navigation";

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

describe("mobile + admin role matrix (F-008)", () => {
  it("partitions every allowed view between primary and more, per role", () => {
    for (const role of ["viewer", "researcher", "admin"] as const) {
      const primary = new Set(mobilePrimaryItemsForRole(role).map((i) => i.id));
      const more = new Set(mobileMoreItemsForRole(role).map((i) => i.id));
      for (const id of [...primary]) {
        expect(more.has(id)).toBe(false);
        expect(isViewAllowed(id, role)).toBe(true);
        expect(isMobileMoreView(id, role)).toBe(false);
      }
      for (const id of [...more]) {
        expect(isMobileMoreView(id, role)).toBe(true);
      }
    }
  });

  it("withholds admin-only views from viewer and researcher on mobile", () => {
    for (const role of ["viewer", "researcher"] as const) {
      const ids = [
        ...mobilePrimaryItemsForRole(role),
        ...mobileMoreItemsForRole(role),
      ].map((i) => i.id);
      expect(ids).not.toContain("admin");
      expect(ids).not.toContain("backup");
      expect(ids).not.toContain("meta-hyperagent");
    }
    const adminIds = [
      ...mobilePrimaryItemsForRole("admin"),
      ...mobileMoreItemsForRole("admin"),
    ].map((i) => i.id);
    expect(adminIds).toContain("admin");
    expect(adminIds).toContain("backup");
  });

  it("withholds researcher views from viewers on mobile", () => {
    const viewerIds = new Set(
      [...mobilePrimaryItemsForRole("viewer"), ...mobileMoreItemsForRole("viewer")].map(
        (i) => i.id,
      ),
    );
    expect(viewerIds.has("loops")).toBe(false);
    expect(viewerIds.has("autoresearch")).toBe(false);
    expect(viewerIds.has("compute")).toBe(false);
  });
});
