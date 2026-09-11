/**
 * OAuth device-flow polling lifecycle for Pi model management (W1
 * readiness-core).
 *
 * The previous `PiModelManagement` effect depended on the whole `activeOAuth`
 * object and called `setActiveOAuth(latest)` with every poll response. Each
 * fresh response object re-ran the effect, which fired an immediate poll and
 * installed a new interval — a render-driven hot loop instead of one poll per
 * 4s. This module keeps two load-bearing invariants in one testable place:
 *
 *   1. exactly one interval drives polling (`startOAuthFlowPolling` owns the
 *      timer; the component effect keys on the primitive flow id + provider);
 *   2. an unchanged status never produces a new state object
 *      (`isSameOAuthFlowStatus`), so adopting a poll result cannot re-trigger
 *      the effect that owns the interval.
 */

export interface OAuthFlowStatusLike {
  flow_id?: string;
  provider?: string;
  status?: string;
  error?: string | null;
}

/** True when adopting `next` over `prev` would change nothing observable. */
export function isSameOAuthFlowStatus(
  prev: OAuthFlowStatusLike | null | undefined,
  next: OAuthFlowStatusLike | null | undefined
): boolean {
  if (prev === next) return true;
  if (!prev || !next) return false;
  return (
    prev.flow_id === next.flow_id &&
    prev.provider === next.provider &&
    prev.status === next.status &&
    (prev.error || null) === (next.error || null)
  );
}

export interface OAuthFlowPollerOptions<T> {
  /** Resolve the latest flow snapshot; `null` means "no matching flow yet". */
  poll: () => Promise<T | null>;
  /** Poll cadence in milliseconds. */
  intervalMs: number;
  /** Receives every non-null snapshot, in poll order. */
  onFlow: (latest: T) => void;
  /** Receives poll rejections (the interval keeps running). */
  onError?: (error: unknown) => void;
}

export interface OAuthFlowPoller {
  stop: () => void;
}

/**
 * Run one immediate poll, then one poll per `intervalMs`, until `stop()`.
 * Late resolutions after `stop()` are dropped so an unmounted component never
 * adopts stale state.
 */
export function startOAuthFlowPolling<T>(
  options: OAuthFlowPollerOptions<T>
): OAuthFlowPoller {
  const { poll, intervalMs, onFlow, onError } = options;
  let stopped = false;
  const tick = async () => {
    if (stopped) return;
    try {
      const latest = await poll();
      if (stopped || latest == null) return;
      onFlow(latest);
    } catch (error) {
      if (stopped) return;
      onError?.(error);
    }
  };
  void tick();
  const timer = setInterval(() => void tick(), intervalMs);
  return {
    stop: () => {
      stopped = true;
      clearInterval(timer);
    },
  };
}
