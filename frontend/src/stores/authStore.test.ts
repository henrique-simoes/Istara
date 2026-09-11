import { afterEach, describe, expect, it, vi } from "vitest";

function memoryStorage() {
  const values = new Map<string, string>();
  return {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value),
    removeItem: (key: string) => values.delete(key),
    clear: () => values.clear(),
  };
}

describe("auth-store bootstrap", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
    vi.resetModules();
  });

  it("hydrates the in-memory token before protected Settings actions run", async () => {
    const localStorage = memoryStorage();
    vi.stubGlobal("localStorage", localStorage);
    vi.stubGlobal("window", {
      location: { protocol: "http:", hostname: "localhost", port: "3000" },
      dispatchEvent: vi.fn(),
    });
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000");

    const fetchMock = vi.fn(async (input: string | URL) => {
      const url = String(input);
      if (url.endsWith("/api/auth/me")) {
        return new Response(JSON.stringify({
          id: "user-1",
          username: "admin",
          email: "admin@example.test",
          role: "admin",
          display_name: "Admin",
        }), { status: 200, headers: { "Content-Type": "application/json" } });
      }
      if (url.endsWith("/api/auth/sessions")) {
        return new Response(JSON.stringify([]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (url.endsWith("/api/webauthn/credentials")) {
        return new Response(JSON.stringify([]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      throw new Error(`Unexpected fetch: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    const { useAuthStore } = await import("./authStore");
    expect(useAuthStore.getState().token).toBeNull();

    localStorage.setItem("istara_token", "fresh-token");
    await expect(useAuthStore.getState().fetchMe()).resolves.toBe(true);

    expect(useAuthStore.getState().token).toBe("fresh-token");
    await expect(useAuthStore.getState().listAuthSessions()).resolves.toEqual([]);
    await expect(useAuthStore.getState().listPasskeys()).resolves.toEqual([]);
  });

  it("lists sessions over the cookie transport when no bearer exists (post-reload custody)", async () => {
    // Memory-only custody leaves no reload-surviving bearer by design; the
    // HttpOnly session cookie (credentials:include) must still authenticate
    // the session-management calls instead of throwing client-side.
    const localStorage = memoryStorage();
    vi.stubGlobal("localStorage", localStorage);
    vi.stubGlobal("window", {
      location: { protocol: "http:", hostname: "localhost", port: "3000" },
      dispatchEvent: vi.fn(),
    });
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000");

    const seen: Array<{ url: string; init?: RequestInit }> = [];
    const fetchMock = vi.fn(async (input: string | URL, init?: RequestInit) => {
      seen.push({ url: String(input), init });
      return new Response(JSON.stringify([]), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    const { useAuthStore } = await import("./authStore");
    expect(useAuthStore.getState().token).toBeNull();

    await expect(useAuthStore.getState().listAuthSessions()).resolves.toEqual([]);
    expect(seen).toHaveLength(1);
    expect(seen[0].init?.credentials).toBe("include");
    expect((seen[0].init?.headers as Record<string, string> | undefined)?.Authorization).toBeUndefined();
  });

  it("lists and deletes passkeys over the cookie transport when no bearer exists (post-reload custody)", async () => {
    // Same custody rule as the session calls: no reload-surviving bearer means
    // the HttpOnly session cookie must authenticate passkey management instead
    // of the store throwing "Not authenticated" client-side.
    const localStorage = memoryStorage();
    vi.stubGlobal("localStorage", localStorage);
    vi.stubGlobal("window", {
      location: { protocol: "http:", hostname: "localhost", port: "3000" },
      dispatchEvent: vi.fn(),
    });
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000");

    const seen: Array<{ url: string; init?: RequestInit }> = [];
    const fetchMock = vi.fn(async (input: string | URL, init?: RequestInit) => {
      seen.push({ url: String(input), init });
      return new Response(JSON.stringify([]), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    const { useAuthStore } = await import("./authStore");
    expect(useAuthStore.getState().token).toBeNull();

    await expect(useAuthStore.getState().listPasskeys()).resolves.toEqual([]);
    await expect(useAuthStore.getState().deletePasskey("cred-1")).resolves.toBeUndefined();

    expect(seen).toHaveLength(2);
    for (const call of seen) {
      expect(call.init?.credentials).toBe("include");
      expect((call.init?.headers as Record<string, string> | undefined)?.Authorization).toBeUndefined();
    }
    expect(seen[0].url).toContain("/api/webauthn/credentials");
    expect(seen[1].url).toContain("/api/webauthn/credentials/cred-1");
    expect(seen[1].init?.method).toBe("DELETE");
  });
});
