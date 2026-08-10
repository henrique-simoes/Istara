export interface MergedModelCatalogEntry {
  name: string;
  engine: "legacy" | "pi";
  switchable: boolean;
  provider_type?: string;
  server_name?: string;
  endpoint_id?: string;
  size?: number;
  [key: string]: unknown;
}

/**
 * Present both routing planes in the existing Settings model inventory.
 * Pi entries are identity-only and therefore intentionally not switchable by
 * the legacy provider switch endpoint.
 */
export function mergeModelCatalogs(
  legacyModels: unknown[] | null | undefined,
  piCatalog: unknown[] | null | undefined,
): MergedModelCatalogEntry[] {
  const merged: MergedModelCatalogEntry[] = [];
  const seenLegacy = new Set<string>();
  const seenPi = new Set<string>();

  for (const raw of legacyModels || []) {
    if (!raw || typeof raw !== "object") continue;
    const model = raw as Record<string, unknown>;
    const name = String(model.name || model.model || "").trim();
    if (!name) continue;
    const key = `${name}\u0000${String(model.server_name || model.provider_type || "")}`;
    if (seenLegacy.has(key)) continue;
    seenLegacy.add(key);
    merged.push({ ...model, name, engine: "legacy", switchable: true });
  }

  for (const raw of piCatalog || []) {
    if (!raw || typeof raw !== "object") continue;
    const model = raw as Record<string, unknown>;
    const name = String(model.model || model.name || "").trim();
    const endpointId = String(model.endpoint_id || "").trim();
    if (!name || !endpointId || seenPi.has(endpointId)) continue;
    seenPi.add(endpointId);
    merged.push({
      ...model,
      name,
      endpoint_id: endpointId,
      provider_type: String(model.provider_kind || model.provider_type || ""),
      server_name: endpointId,
      engine: "pi",
      switchable: false,
    });
  }

  return merged;
}
