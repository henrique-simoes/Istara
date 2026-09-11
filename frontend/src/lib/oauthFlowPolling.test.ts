import { describe, expect, it, vi } from "vitest";

import {
  isSameOAuthFlowStatus,
  startOAuthFlowPolling,
} from "./oauthFlowPolling";

describe("isSameOAuthFlowStatus", () => {
  it("treats identical references and equal snapshots as unchanged", () => {
    const flow = { flow_id: "f1", provider: "openai", status: "pending" };
    expect(isSameOAuthFlowStatus(flow, flow)).toBe(true);
    expect(
      isSameOAuthFlowStatus(flow, { flow_id: "f1", provider: "openai", status: "pending" })
    ).toBe(true);
    // Missing vs empty error normalise to the same state.
    expect(
      isSameOAuthFlowStatus(flow, { ...flow, error: undefined })
    ).toBe(true);
  });

  it("detects status, flow, provider, and error transitions", () => {
    const prev = { flow_id: "f1", provider: "openai", status: "pending" };
    expect(
      isSameOAuthFlowStatus(prev, { ...prev, status: "approved" })
    ).toBe(false);
    expect(
      isSameOAuthFlowStatus(prev, { ...prev, flow_id: "f2" })
    ).toBe(false);
    expect(
      isSameOAuthFlowStatus(prev, { ...prev, provider: "google" })
    ).toBe(false);
    expect(
      isSameOAuthFlowStatus(prev, { ...prev, status: "failed", error: "denied" })
    ).toBe(false);
    expect(isSameOAuthFlowStatus(prev, null)).toBe(false);
    expect(isSameOAuthFlowStatus(null, prev)).toBe(false);
  });
});

describe("startOAuthFlowPolling", () => {
  it("polls immediately, then exactly once per interval (no hot loop)", async () => {
    vi.useFakeTimers();
    try {
      const poll = vi.fn(async () => ({ status: "pending" }));
      const onFlow = vi.fn();
      const poller = startOAuthFlowPolling({ poll, intervalMs: 4000, onFlow });
      // Immediate first poll resolves on the microtask queue.
      await vi.advanceTimersByTimeAsync(0);
      expect(poll).toHaveBeenCalledTimes(1);
      expect(onFlow).toHaveBeenCalledTimes(1);
      // Ten seconds of wall time must produce exactly two more polls.
      await vi.advanceTimersByTimeAsync(10_000);
      expect(poll).toHaveBeenCalledTimes(3);
      expect(onFlow).toHaveBeenCalledTimes(3);
      poller.stop();
    } finally {
      vi.useRealTimers();
    }
  });

  it("stop() installs no further polls and drops late resolutions", async () => {
    vi.useFakeTimers();
    try {
      let release!: (value: { status: string }) => void;
      const poll = vi.fn(
        () => new Promise<{ status: string }>((resolve) => { release = resolve; })
      );
      const onFlow = vi.fn();
      const poller = startOAuthFlowPolling({ poll, intervalMs: 4000, onFlow });
      expect(poll).toHaveBeenCalledTimes(1);
      poller.stop();
      release({ status: "approved" });
      await vi.advanceTimersByTimeAsync(60_000);
      // The in-flight resolution was dropped and no interval tick ever ran.
      expect(onFlow).not.toHaveBeenCalled();
      expect(poll).toHaveBeenCalledTimes(1);
    } finally {
      vi.useRealTimers();
    }
  });

  it("ignores null snapshots and surfaces poll errors without stopping", async () => {
    vi.useFakeTimers();
    try {
      const poll = vi
        .fn<() => Promise<{ status: string } | null>>()
        .mockResolvedValueOnce(null)
        .mockRejectedValueOnce(new Error("network down"))
        .mockResolvedValue({ status: "pending" });
      const onFlow = vi.fn();
      const onError = vi.fn();
      const poller = startOAuthFlowPolling({ poll, intervalMs: 4000, onFlow, onError });
      await vi.advanceTimersByTimeAsync(0);
      expect(onFlow).not.toHaveBeenCalled();
      await vi.advanceTimersByTimeAsync(4000);
      expect(onError).toHaveBeenCalledTimes(1);
      await vi.advanceTimersByTimeAsync(4000);
      expect(onFlow).toHaveBeenCalledTimes(1);
      poller.stop();
    } finally {
      vi.useRealTimers();
    }
  });
});
