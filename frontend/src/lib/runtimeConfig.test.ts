import { afterEach, describe, expect, it, vi } from "vitest";

import { getApiBase, getWsBase } from "./runtimeConfig";

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
});
