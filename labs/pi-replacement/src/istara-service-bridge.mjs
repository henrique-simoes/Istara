import {
  ISTARA_SURFACE_MAP,
  buildSurfaceCoverageSummary,
  scenarioSurfaceIds,
  surfaceById,
} from "./istara-surface-map.mjs";

const jsonClone = (value) => JSON.parse(JSON.stringify(value));

export class IstaraServiceBridge {
  constructor(options = {}) {
    this.facade = options.facade ?? null;
    this.scenarios = options.scenarios ?? [];
    this.surfaceMap = ISTARA_SURFACE_MAP;
  }

  describeScenario(scenario) {
    const surfaceIds = scenarioSurfaceIds(scenario);
    return {
      scenarioId: scenario.id,
      title: scenario.title,
      requiredTools: [...(scenario.requiredTools ?? [])],
      istaraSurfaceIds: surfaceIds,
      realSurfaces: surfaceIds.map((surfaceId) => {
        const surface = surfaceById(surfaceId);
        return surface
          ? {
              id: surface.id,
              label: surface.label,
              category: surface.category,
              bridgeStatus: surface.bridgeStatus,
              realFiles: surface.realFiles,
              realTests: surface.realTests,
              productionGaps: surface.productionGaps,
            }
          : { id: surfaceId, missing: true };
      }),
    };
  }

  coverageSummary(scenarios = this.scenarios) {
    return buildSurfaceCoverageSummary(scenarios);
  }

  blockedProductionGaps(scenarios = this.scenarios) {
    const requested = new Set();
    for (const scenario of scenarios) {
      for (const surfaceId of scenarioSurfaceIds(scenario)) requested.add(surfaceId);
    }
    return ISTARA_SURFACE_MAP
      .filter((surface) => requested.size === 0 || requested.has(surface.id))
      .flatMap((surface) =>
        surface.productionGaps.map((gap) => ({
          surfaceId: surface.id,
          surfaceLabel: surface.label,
          reason: gap.reason,
          files: gap.files,
        })),
      );
  }

  toolCoverage(scenarios = this.scenarios) {
    const tools = new Set(scenarios.flatMap((scenario) => scenario.requiredTools ?? []));
    return ISTARA_SURFACE_MAP.map((surface) => ({
      surfaceId: surface.id,
      coveredToolCount: surface.bridgeTools.filter((toolId) => tools.has(toolId)).length,
      requiredBridgeToolCount: surface.bridgeTools.length,
      missingBridgeTools: surface.bridgeTools.filter((toolId) => !tools.has(toolId)),
    }));
  }

  snapshot(scenarios = this.scenarios) {
    const facadeSnapshot = this.facade?.snapshot ? this.facade.snapshot() : null;
    return {
      surfaceCoverage: this.coverageSummary(scenarios),
      toolCoverage: this.toolCoverage(scenarios),
      blockedProductionGaps: this.blockedProductionGaps(scenarios),
      facade: facadeSnapshot ? jsonClone(facadeSnapshot) : null,
    };
  }
}

export function buildBridgeSnapshot(options = {}) {
  return new IstaraServiceBridge(options).snapshot(options.scenarios ?? []);
}
