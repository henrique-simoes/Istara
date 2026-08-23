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

