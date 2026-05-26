export type GlobalUserRole = "admin" | "researcher" | "viewer" | string | null | undefined;
export type ProjectUserRole = "project_admin" | "researcher" | "viewer" | string | null | undefined;

export interface RoleCapabilityInput {
  globalRole?: GlobalUserRole;
  projectRole?: ProjectUserRole;
  teamMode?: boolean;
}

export interface RoleCapabilities {
  isGlobalAdmin: boolean;
  isProjectAdmin: boolean;
  canReadActiveProject: boolean;
  canWriteActiveProject: boolean;
  canAdminActiveProject: boolean;
  canManageSystemSettings: boolean;
  canManageAuthUsers: boolean;
  canManageConnectionStrings: boolean;
  canManageTelemetry: boolean;
  canManageLlmInfrastructure: boolean;
  canUseGovernedEvolution: boolean;
  canUseSteering: boolean;
  canManageProjectAgents: boolean;
  canManageProjectIntegrations: boolean;
}

export function isGlobalAdminRole(role?: GlobalUserRole): boolean {
  return role === "admin";
}

export function isProjectAdminRole(role?: ProjectUserRole): boolean {
  return role === "project_admin";
}

export function canWriteProjectRole(projectRole?: ProjectUserRole, globalRole?: GlobalUserRole): boolean {
  return isGlobalAdminRole(globalRole) || projectRole === "researcher" || isProjectAdminRole(projectRole);
}

export function canAdminProjectRole(projectRole?: ProjectUserRole, globalRole?: GlobalUserRole): boolean {
  return isGlobalAdminRole(globalRole) || isProjectAdminRole(projectRole);
}

export function buildRoleCapabilities({
  globalRole,
  projectRole,
  teamMode = true,
}: RoleCapabilityInput): RoleCapabilities {
  const isGlobalAdmin = isGlobalAdminRole(globalRole);
  const isProjectAdmin = isProjectAdminRole(projectRole);
  const localSystemAccess = !teamMode || isGlobalAdmin;
  const canAdminActiveProject = canAdminProjectRole(projectRole, globalRole);

  return {
    isGlobalAdmin,
    isProjectAdmin,
    canReadActiveProject: Boolean(projectRole) || isGlobalAdmin,
    canWriteActiveProject: canWriteProjectRole(projectRole, globalRole),
    canAdminActiveProject,
    canManageSystemSettings: localSystemAccess,
    canManageAuthUsers: localSystemAccess,
    canManageConnectionStrings: localSystemAccess,
    canManageTelemetry: localSystemAccess,
    canManageLlmInfrastructure: localSystemAccess,
    canUseGovernedEvolution: localSystemAccess,
    canUseSteering: localSystemAccess,
    canManageProjectAgents: canAdminActiveProject,
    canManageProjectIntegrations: canAdminActiveProject,
  };
}
