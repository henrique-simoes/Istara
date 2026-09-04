export const CUSTOM_LOOP_INTERVAL_MIN_SECONDS = 60;
export const CUSTOM_LOOP_INTERVAL_MAX_SECONDS = 86_400;

export function isCustomLoopIntervalValid(value: number | ""): boolean {
  return (
    typeof value === "number" &&
    Number.isInteger(value) &&
    value >= CUSTOM_LOOP_INTERVAL_MIN_SECONDS &&
    value <= CUSTOM_LOOP_INTERVAL_MAX_SECONDS
  );
}

export function customLoopIntervalError(value: number | ""): string | null {
  if (value === "") return "Enter an interval between 60 and 86400 seconds.";
  if (!isCustomLoopIntervalValid(value)) {
    return "Interval must be a whole number between 60 and 86400 seconds.";
  }
  return null;
}
