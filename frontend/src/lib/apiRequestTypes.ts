export interface DataIntegrityQuarantineRequest {
  dry_run?: boolean;
}

export interface ProfileUpdateRequest {
  current_password: string;
  username?: string;
  email?: string;
  display_name?: string;
}

export interface PasswordChangeRequest {
  current_password: string;
  new_password: string;
}

export interface FileEncryptionEnableRequest {
  confirm_loss_warning: boolean;
}

export interface FileEncryptionRotateRequest {
  confirm_rotation: boolean;
}

export interface LLMServerCreate {
  name: string;
  provider_type: "ollama" | "lmstudio" | "openai_compat" | "gemini_openai" | string;
  host: string;
  api_key?: string;
  is_local?: boolean;
  priority?: number;
}

export interface LLMServerUpdate {
  name?: string;
  host?: string;
  api_key?: string;
  priority?: number;
  is_local?: boolean;
}
