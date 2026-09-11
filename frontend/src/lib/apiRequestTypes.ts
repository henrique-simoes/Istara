export interface DataIntegrityQuarantineRequest {
  dry_run?: boolean;
}

// Benchmark-only Research Spine receipt route (explicit opt-in; not a user-facing
// client operation): /{project_id}/synthetic-reconciliation

/** Benchmark-only receipt; never promotes an application or satisfies human review. */
export interface SyntheticReconciliationAction {
  code_application_id: string;
  decision_type: string;
  rationale?: string;
  accepted_code_id?: string;
}

/** Explicitly opt-in benchmark request; production UI must not invoke this route. */
export interface SyntheticReconciliationRequest {
  coding_run_id: string;
  diagnostic_id: string;
  decisions: SyntheticReconciliationAction[];
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
