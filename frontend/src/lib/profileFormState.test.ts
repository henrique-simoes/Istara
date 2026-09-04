import { describe, expect, it } from "vitest";

import { needsProfileHydration, profileFormValues } from "./profileFormState";

describe("profile form state", () => {
  it("requests one authoritative refresh when a team identity is incomplete", () => {
    expect(needsProfileHydration({ id: "user-1", username: "", email: "" })).toBe(true);
    expect(needsProfileHydration({ id: "user-1", username: "admin", email: "admin@example.test" })).toBe(false);
    expect(needsProfileHydration({ id: "local", username: "local", email: "" })).toBe(false);
    expect(needsProfileHydration(null)).toBe(false);
  });

  it("keeps safe blank values while preferring display name then username", () => {
    expect(profileFormValues({ id: "user-1", username: "admin", email: "admin@example.test", display_name: "Researcher" })).toEqual({
      username: "admin",
      email: "admin@example.test",
      displayName: "Researcher",
    });
    expect(profileFormValues({ id: "user-1", username: "admin", email: "", display_name: "" })).toEqual({
      username: "admin",
      email: "",
      displayName: "admin",
    });
  });
});
