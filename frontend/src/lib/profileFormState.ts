export interface ProfileIdentity {
  id?: string | null;
  username?: string | null;
  email?: string | null;
  display_name?: string | null;
}

export interface ProfileFormValues {
  username: string;
  email: string;
  displayName: string;
}

export function needsProfileHydration(user: ProfileIdentity | null | undefined): boolean {
  if (!user || user.id === "local") return false;
  return !user.username?.trim() || !user.email?.trim();
}

export function profileFormValues(user: ProfileIdentity | null | undefined): ProfileFormValues {
  const username = user?.username || "";
  return {
    username,
    email: user?.email || "",
    displayName: user?.display_name || username,
  };
}
