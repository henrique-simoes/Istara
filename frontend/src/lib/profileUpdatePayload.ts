export interface ProfileUpdateFormValues {
  currentPassword: string;
  username: string;
  email: string;
  displayName: string;
}

export interface ProfileUpdatePayload {
  current_password: string;
  username?: string;
  email?: string;
  display_name: string;
}

/**
 * Build a profile update without turning redacted optional PII into a clear.
 * The API treats omitted username/email fields as unchanged and validates any
 * non-empty replacement. An empty email can mean decryption was unavailable,
 * so it must never be sent as an attempted replacement.
 */
export function buildProfileUpdatePayload(values: ProfileUpdateFormValues): ProfileUpdatePayload {
  const payload: ProfileUpdatePayload = {
    current_password: values.currentPassword,
    display_name: values.displayName,
  };
  const username = values.username.trim();
  const email = values.email.trim();
  if (username) payload.username = values.username;
  if (email) payload.email = values.email;
  return payload;
}
