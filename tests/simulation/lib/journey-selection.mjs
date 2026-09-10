/**
 * Fail-closed journey selection for the container-first ui-journeys lane
 * (remediation plan W2.2-W2.3, blocker B1 — testing-to-main-remediation-20260909).
 *
 * The ui-journeys CI job and local runs must agree on one selection contract:
 *
 *   - the proven set is `smoke ∪ proven-extra`; every entry is an exact
 *     registered scenario id (never a substring, never duplicated);
 *   - every registered scenario is accounted for EXACTLY once: either selected
 *     (proven) or an explicit not_runnable ledger entry with a specific reason;
 *   - scenarios declared in `releaseObligationIds` are named individually as
 *     pending credential-free release obligations — a generic blanket reason
 *     ("not yet proven") is not allowed to describe them;
 *   - an empty selected scope fails closed, and so does an invalid scope.
 *
 * Importability of every registered scenario is checked by the caller (CI
 * resolve step) BEFORE the QA stack starts; a scenario that cannot be imported
 * is a release failure, not a warning that silently shrinks the executable set.
 */

import { releaseObligationIds } from "./scenario-registry.mjs";

const RELEASE_OBLIGATIONS = new Set(releaseObligationIds);

const GENERIC_REASON = "unproven on the container ui-journeys lane — the proven set grows only with dated run evidence (D.8)";
const RELEASE_OBLIGATION_REASON =
  "credential-free release obligation (remediation B1/B4/B5): shipped and registered but never executed — first run owned by the container ui-journeys lane";

function isStringArray(value) {
  return Array.isArray(value) && value.every((entry) => typeof entry === "string");
}

export function resolveJourneySelection({ registered, smoke, extra, scope }) {
  const errors = [];

  if (!isStringArray(registered) || registered.length === 0) {
    return {
      selected: [],
      notRunnable: [],
      errors: ["scenario registry is empty or malformed"],
      registeredCount: Array.isArray(registered) ? registered.length : 0,
      provenCount: 0,
      releaseObligationsPending: 0,
    };
  }
  if (!isStringArray(smoke) || !isStringArray(extra)) {
    errors.push("smoke and proven-extra journey lists must be string arrays");
  }
  if (scope !== "smoke" && scope !== "full") {
    errors.push(`unknown journey scope "${scope}" — expected "smoke" or "full"`);
  }

  const registeredSet = new Set(registered);
  // Duplicates inside the registry itself break the selection bijection the
  // same way list-level duplicates do (N-R1): fail closed here so the CI
  // resolve step refuses a duplicated registry before the QA stack starts.
  const seenRegistered = new Set();
  for (const id of registered) {
    if (seenRegistered.has(id)) {
      errors.push(`duplicate scenario id "${id}" in the registry — the selection must be a bijection`);
    }
    seenRegistered.add(id);
  }
  const smokeList = Array.isArray(smoke) ? smoke : [];
  const extraList = Array.isArray(extra) ? extra : [];

  for (const [listName, list] of [["smoke", smokeList], ["proven-extra", extraList]]) {
    const seen = new Set();
    for (const id of list) {
      if (!registeredSet.has(id)) {
        errors.push(`unknown scenario id "${id}" in ${listName} — every journey id must exist in the registry verbatim`);
      }
      if (seen.has(id)) {
        errors.push(`duplicate scenario id "${id}" in ${listName} — the selection must be a bijection`);
      }
      seen.add(id);
    }
  }
  for (const id of smokeList) {
    if (extraList.includes(id)) {
      errors.push(`duplicate scenario id "${id}" across smoke and proven-extra — the selection must be a bijection`);
    }
  }

  const provenSet = new Set([...smokeList, ...extraList]);
  const notRunnable = registered
    .filter((id) => !provenSet.has(id))
    .map((id) =>
      RELEASE_OBLIGATIONS.has(id)
        ? { scenario: id, release_obligation: true, reason: RELEASE_OBLIGATION_REASON }
        : { scenario: id, reason: GENERIC_REASON },
    );

  const proven = registered.filter((id) => provenSet.has(id));
  const selected = scope === "full" ? proven : smokeList.filter((id) => registeredSet.has(id));

  if (errors.length === 0 && selected.length === 0) {
    errors.push(
      scope === "full"
        ? "no-journeys-selected — the full proven scope is empty; proven journeys may never silently vanish"
        : "no-journeys-selected — the smoke scope is empty",
    );
  }

  return {
    selected,
    notRunnable,
    errors,
    registeredCount: registered.length,
    provenCount: proven.length,
    releaseObligationsPending: notRunnable.filter((entry) => entry.release_obligation).length,
  };
}

/** One-line human summary for the CI log (scope/selected/not_runnable accounting). */
export function explainSelection(selection) {
  const obligations = selection.releaseObligationsPending
    ? ` release_obligations_pending=${selection.releaseObligationsPending}`
    : "";
  return `registered=${selection.registeredCount} proven=${selection.provenCount} selected=${selection.selected.length} not_runnable=${selection.notRunnable.length}${obligations}`;
}
