import { describe, expect, it } from "vitest";

import { buildProfileUpdatePayload } from "./profileUpdatePayload";

describe("buildProfileUpdatePayload", () => {
  it("omits a redacted empty email instead of submitting an invalid replacement", () => {
    expect(
      buildProfileUpdatePayload({
        currentPassword: "current-secret",
        username: "admin",
        email: "",
        displayName: "Admin",
      }),
    ).toEqual({
      current_password: "current-secret",
      username: "admin",
      display_name: "Admin",
    });
  });

  it("keeps non-empty email replacements for backend validation", () => {
    expect(
      buildProfileUpdatePayload({
        currentPassword: "current-secret",
        username: "admin",
        email: "new@example.com",
        displayName: "Admin",
      }).email,
    ).toBe("new@example.com");
  });

  it("omits an unexpectedly blank username while preserving display name edits", () => {
    expect(
      buildProfileUpdatePayload({
        currentPassword: "current-secret",
        username: "   ",
        email: "",
        displayName: "New name",
      }),
    ).toEqual({ current_password: "current-secret", display_name: "New name" });
  });
});
