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
});
