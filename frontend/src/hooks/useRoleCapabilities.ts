"use client";

import { useMemo } from "react";
import { buildRoleCapabilities } from "@/lib/roleCapabilities";
import { useAuthStore } from "@/stores/authStore";
import { useProjectStore } from "@/stores/projectStore";

export function useRoleCapabilities() {
  const { user, teamMode } = useAuthStore();
  const projectRole = useProjectStore((state) =>
    state.projects.find((project) => project.id === state.activeProjectId)?.current_user_project_role
  );

  return useMemo(
    () => buildRoleCapabilities({
      globalRole: user?.role,
      projectRole,
      teamMode,
    }),
    [user?.role, projectRole, teamMode],
  );
}
