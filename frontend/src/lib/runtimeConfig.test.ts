import { afterEach, describe, expect, it, vi } from "vitest";

import { getApiBase, getWsBase } from "./runtimeConfig";

/**
 * Mutation-hardened suite for runtimeConfig.
 *
 * Each test pins one observable contract of the URL derivation so that
 * Stryker mutants (operator swaps, literal tweaks, guard flips) change the
 * asserted outcome. The loopback-alignment matrix deliberately uses a
 * hostname MISMATCH between the configured URL and the browser origin —
 * that is the only condition under which every protocol-rewrite branch is
 * observable in the returned string.
 */
describe("runtimeConfig", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it("prefers public API and websocket environment overrides without trailing slash", () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", " https://api.istara.example/ ");
    vi.stubEnv("NEXT_PUBLIC_WS_URL", " wss://ws.istara.example/ ");

    expect(getApiBase()).toBe("https://api.istara.example");
    expect(getWsBase()).toBe("wss://ws.istara.example");
  });

  it("aligns loopback overrides with the browser hostname to preserve same-site auth", () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://127.0.0.1:8000/");
    vi.stubEnv("NEXT_PUBLIC_WS_URL", "ws://127.0.0.1:8000/");
    vi.stubGlobal("window", {
      location: {
        protocol: "http:",
        hostname: "localhost",
        port: "3000",
      },
    });

    expect(getApiBase()).toBe("http://localhost:8000");
    expect(getWsBase()).toBe("ws://localhost:8000");
  });

  it("keeps explicit non-loopback overrides authoritative", () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "https://api.istara.example/");
    vi.stubEnv("NEXT_PUBLIC_WS_URL", "wss://ws.istara.example/");
    vi.stubGlobal("window", {
      location: {
        protocol: "http:",
        hostname: "localhost",
        port: "3000",
      },
    });

    expect(getApiBase()).toBe("https://api.istara.example");
    expect(getWsBase()).toBe("wss://ws.istara.example");
  });

  it("derives browser-local API and websocket bases from the current origin", () => {
    vi.stubGlobal("window", {
      location: {
        protocol: "https:",
        hostname: "istara.local",
      },
    });

    expect(getApiBase()).toBe("https://istara.local:8000");
    expect(getWsBase()).toBe("wss://istara.local:8000");
  });

  it("uses ws for non-TLS browser origins", () => {
    vi.stubGlobal("window", {
      location: {
        protocol: "http:",
        hostname: "istara.local",
      },
    });

    expect(getApiBase()).toBe("http://istara.local:8000");
    expect(getWsBase()).toBe("ws://istara.local:8000");
  });

  it("falls back when the browser hostname is unavailable", () => {
    vi.stubGlobal("window", {
      location: {
        protocol: "https:",
        hostname: "",
      },
    });

    expect(getApiBase()).toBe("http://localhost:8000");
    expect(getWsBase()).toBe("ws://localhost:8000");
  });

  it("falls back to localhost when no browser origin or public setting exists", () => {
    delete process.env.NEXT_PUBLIC_API_URL;
    delete process.env.NEXT_PUBLIC_WS_URL;
    vi.stubGlobal("window", undefined);

    expect(() => getApiBase()).not.toThrow();
    expect(() => getWsBase()).not.toThrow();
    expect(getApiBase()).toBe("http://localhost:8000");
    expect(getWsBase()).toBe("ws://localhost:8000");
  });

  // --- Loopback alignment: protocol rewrite matrix -----------------------
  // The override host (127.0.0.1) differs from the browser host so the
  // rewrite is observable in the returned string.

  it("rewrites ws overrides to wss when the browser origin is https", () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://127.0.0.1:8000");
    vi.stubEnv("NEXT_PUBLIC_WS_URL", "ws://127.0.0.1:8000");
    vi.stubGlobal("window", {
      location: { protocol: "https:", hostname: "localhost", port: "3000" },
    });

    expect(getApiBase()).toBe("https://localhost:8000");
    expect(getWsBase()).toBe("wss://localhost:8000");
  });

  it("keeps wss overrides on wss when the browser origin is https", () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "https://127.0.0.1:8000");
    vi.stubEnv("NEXT_PUBLIC_WS_URL", "wss://127.0.0.1:8000");
    vi.stubGlobal("window", {
      location: { protocol: "https:", hostname: "localhost", port: "3000" },
    });

    expect(getApiBase()).toBe("https://localhost:8000");
    expect(getWsBase()).toBe("wss://localhost:8000");
  });

  it("normalizes plain https overrides to https when the browser origin is https", () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "https://127.0.0.1:8000");
    vi.stubGlobal("window", {
      location: { protocol: "https:", hostname: "localhost", port: "3000" },
    });

    expect(getApiBase()).toBe("https://localhost:8000");
  });

  it("rewrites ws overrides to ws when the browser origin is http", () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://127.0.0.1:8000");
    vi.stubEnv("NEXT_PUBLIC_WS_URL", "ws://127.0.0.1:8000");
    vi.stubGlobal("window", {
      location: { protocol: "http:", hostname: "localhost", port: "3000" },
    });

    expect(getApiBase()).toBe("http://localhost:8000");
    expect(getWsBase()).toBe("ws://localhost:8000");
  });

  it("downgrades wss overrides to ws when the browser origin is http", () => {
    vi.stubEnv("NEXT_PUBLIC_WS_URL", "wss://127.0.0.1:8000");
    vi.stubGlobal("window", {
      location: { protocol: "http:", hostname: "localhost", port: "3000" },
    });

    expect(getWsBase()).toBe("ws://localhost:8000");
  });

  it("rewrites http overrides to http when the browser origin is http and hosts differ", () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://127.0.0.1:8080");
    vi.stubGlobal("window", {
      location: { protocol: "http:", hostname: "localhost", port: "3000" },
    });

    expect(getApiBase()).toBe("http://localhost:8080");
  });

  // --- Loopback host contracts (isLoopbackHost) --------------------------

  it("treats the bare IPv6 loopback hostname ::1 as loopback", () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://127.0.0.1:8000");
    vi.stubGlobal("window", {
      location: { protocol: "http:", hostname: "::1", port: "3000" },
    });

    // URL.hostname normalises ::1 to [::1] when the override is aligned.
    expect(getApiBase()).toBe("http://[::1]:8000");
  });

  it("does not treat a malformed 127-prefix host as loopback (regex end anchor)", () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://127.0.0.1:8000");
    vi.stubGlobal("window", {
      location: { protocol: "http:", hostname: "127.0.0.1999", port: "3000" },
    });

    // Browser host is not loopback, so the override stays authoritative.
    expect(getApiBase()).toBe("http://127.0.0.1:8000");
  });

  it("does not treat a 127-infix host as loopback (regex start anchor)", () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://127.0.0.1:8000");
    vi.stubGlobal("window", {
      location: { protocol: "http:", hostname: "2127.0.0.1", port: "3000" },
    });

    expect(getApiBase()).toBe("http://127.0.0.1:8000");
  });

  it("does not treat a loopback-prefixed domain as loopback (regex end anchor)", () => {
    // The browser hostname must be a valid domain (not an invalid IPv4 literal,
    // which WHATWG host parsing would reject and make the rewrite a no-op) so
    // that a missing end anchor is observable in the returned URL.
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://127.0.0.1:8000");
    vi.stubGlobal("window", {
      location: { protocol: "http:", hostname: "127.0.0.1foo", port: "3000" },
    });

    expect(getApiBase()).toBe("http://127.0.0.1:8000");
  });

  it("aligns multi-digit loopback octets (regex digit bound)", () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://127.0.0.1:8000");
    vi.stubGlobal("window", {
      location: { protocol: "http:", hostname: "127.0.0.100", port: "3000" },
    });

    expect(getApiBase()).toBe("http://127.0.0.100:8000");
  });

  it("trims surrounding whitespace from the browser hostname before the loopback check", () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://127.0.0.1:8000");
    vi.stubGlobal("window", {
      location: { protocol: "http:", hostname: "  localhost  ", port: "3000" },
    });

    expect(getApiBase()).toBe("http://localhost:8000");
  });

  // --- Guards ------------------------------------------------------------

  it("returns the normalized override without touching window when window is undefined", () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://127.0.0.1:8000");
    vi.stubGlobal("window", undefined);

    expect(getApiBase()).toBe("http://127.0.0.1:8000");
  });

  it("returns the normalized ws override without touching window when window is undefined", () => {
    vi.stubEnv("NEXT_PUBLIC_WS_URL", "ws://127.0.0.1:8000");
    vi.stubGlobal("window", undefined);

    expect(getWsBase()).toBe("ws://127.0.0.1:8000");
  });

  it("reads an unset public API setting without throwing (optional chaining guard)", () => {
    delete process.env.NEXT_PUBLIC_API_URL;
    vi.stubGlobal("window", {
      location: { protocol: "http:", hostname: "istara.local", port: "3000" },
    });

    expect(getApiBase()).toBe("http://istara.local:3000");
  });

  it("derives the websocket base from the current origin including an explicit port", () => {
    vi.stubGlobal("window", {
      location: { protocol: "https:", hostname: "istara.local", port: "13080" },
    });

    expect(getApiBase()).toBe("https://istara.local:13080");
    expect(getWsBase()).toBe("wss://istara.local:13080");
  });

  it("uses the default backend port when the browser origin has no explicit port", () => {
    vi.stubGlobal("window", {
      location: { protocol: "http:", hostname: "istara.local", port: "" },
    });

    expect(getApiBase()).toBe("http://istara.local:8000");
    expect(getWsBase()).toBe("ws://istara.local:8000");
  });

  // --- Malformed overrides: the normalization catch path -----------------
  // A syntactically invalid override must be returned untouched by the
  // alignLoopbackUrlWithBrowser catch block, never crash the accessor.

  it("returns a malformed API override untouched instead of throwing", () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://[::1:8000"); // unclosed IPv6 bracket: invalid URL
    vi.stubGlobal("window", {
      location: { protocol: "http:", hostname: "localhost", port: "3000" },
    });

    expect(getApiBase()).toBe("http://[::1:8000");
  });

  it("returns a malformed ws override untouched instead of throwing", () => {
    vi.stubEnv("NEXT_PUBLIC_WS_URL", "ws://[::1:8000"); // unclosed IPv6 bracket: invalid URL
    vi.stubGlobal("window", {
      location: { protocol: "http:", hostname: "localhost", port: "3000" },
    });

    expect(getWsBase()).toBe("ws://[::1:8000");
  });
});
