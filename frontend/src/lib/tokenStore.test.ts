import { describe, expect, it, beforeEach } from "vitest";

import { clearToken, getToken, hasToken, setToken } from "./tokenStore";

function legacyGet(): string | null {
  try {
    return localStorage.getItem("istara_token");
  } catch {
    return null;
  }
}

function legacySet(value: string): void {
  try {
    localStorage.setItem("istara_token", value);
  } catch {
    /* DOM storage unavailable in this runner */
  }
}

function legacyClear(): void {
  try {
    localStorage.clear();
  } catch {
    /* ignore */
  }
}

describe("tokenStore custody", () => {
  beforeEach(() => {
    clearToken();
    legacyClear();
  });

  it("holds fresh tokens in memory without touching localStorage", () => {
    setToken("fresh-token");
    expect(getToken()).toBe("fresh-token");
    expect(hasToken()).toBe(true);
    expect(legacyGet()).toBeNull();
  });

  it("reads legacy localStorage tokens as a fallback", () => {
    legacySet("legacy-token");
    // getToken must agree with whatever the underlying storage holds.
    expect(getToken()).toBe(legacyGet());
  });

  it("prefers memory over the legacy fallback", () => {
    legacySet("legacy-token");
    setToken("memory-token");
    expect(getToken()).toBe("memory-token");
  });

  it("clearToken wipes both memory and legacy storage", () => {
    legacySet("legacy-token");
    setToken("memory-token");
    clearToken();
    expect(getToken()).toBeNull();
    expect(hasToken()).toBe(false);
    expect(legacyGet()).toBeNull();
  });
});
