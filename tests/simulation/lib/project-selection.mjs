export const SIMULATION_PROJECT_NAME = "[SIM] Istara Simulation Project";

export function isSimulationProject(project) {
  const name = String(project?.name || "");
  return name.startsWith("[SIM]") || name.startsWith("[SIM-");
}

export function selectCanonicalSimulationProject(projects, canonicalName = SIMULATION_PROJECT_NAME) {
  const allProjects = Array.isArray(projects) ? projects : [];
  const simProjects = allProjects.filter(isSimulationProject);
  const canonical = simProjects.find((project) => project?.name === canonicalName) || null;
  const staleProjects = simProjects.filter((project) => !canonical || project?.id !== canonical.id);

  return {
    canonical,
    simProjects,
    staleProjects,
  };
}

export function requireActiveProjectId(projectId, surface = "simulation harness") {
  const normalized = String(projectId || "").trim();
  if (!normalized) {
    throw new Error(`${surface} requires an explicit active project_id`);
  }
  return normalized;
}

export function projectScopedPath(path, projectId, surface = path) {
  const scopedProjectId = requireActiveProjectId(projectId, surface);
  const [pathname, query = ""] = String(path).split("?");
  const params = new URLSearchParams(query);
  params.set("project_id", scopedProjectId);
  return `${pathname}?${params.toString()}`;
}
