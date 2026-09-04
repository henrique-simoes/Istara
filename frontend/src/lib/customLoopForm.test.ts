import { describe, expect, it } from "vitest";
import {
  CUSTOM_LOOP_INTERVAL_MAX_SECONDS,
  CUSTOM_LOOP_INTERVAL_MIN_SECONDS,
  customLoopIntervalError,
  isCustomLoopIntervalValid,
} from "./customLoopForm";

describe("custom loop form interval validation", () => {
  it("accepts the backend contract bounds", () => {
    expect(isCustomLoopIntervalValid(CUSTOM_LOOP_INTERVAL_MIN_SECONDS)).toBe(true);
    expect(isCustomLoopIntervalValid(CUSTOM_LOOP_INTERVAL_MAX_SECONDS)).toBe(true);
  });

  it.each(["", 0, 59, 86_401, 1.5])("rejects an invalid interval %s", (value) => {
    expect(isCustomLoopIntervalValid(value as number | "")).toBe(false);
    expect(customLoopIntervalError(value as number | "")).toBeTruthy();
  });

  it("returns no error for a valid interval", () => {
    expect(customLoopIntervalError(300)).toBeNull();
  });
});
