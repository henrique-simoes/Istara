---
stable_id: settings.file-encryption
title: File And Backup Encryption
ui_path: Settings > File And Backup Encryption
audience: architecture
status: documented
related_features: ["settings.users", "settings.security-factors", "documents.upload"]
related_glossary: []
code_references: ["frontend/src/components/settings/FileEncryptionManager.tsx", "backend/app/core/file_encryption.py", "backend/app/services/file_encryption_migration.py", "backend/app/api/routes/settings.py", "backend/app/api/routes/files.py", "backend/app/api/routes/documents.py", "backend/app/core/backup_manager.py"]
api_references: ["backend/app/api/routes/settings.py", "backend/app/api/routes/backup.py"]
test_references: ["tests/test_file_encryption.py", "tests/test_backup.py"]
last_verified: 2026-05-22
compass: CF-SPEC-134 / CF-1671
---

# File And Backup Encryption Architecture

## Implementation Summary

Global admins can enable managed file encryption from Settings. When enabled, Istara encrypts managed uploads, stored document text, and future backup archives at rest. Backups are written as `.tar.gz.enc` and restore/verify paths decrypt only when the configured file-encryption key is available.

## Frontend Surface

- `frontend/src/components/settings/FileEncryptionManager.tsx`
- Mounted through `frontend/src/components/common/SettingsView.tsx`

## State, API, And Backend Contracts

- `GET /api/settings/file-encryption/status` reports enabled state, key availability, key fingerprint, storage mode, and managed-file migration counts without exposing key material.
- `POST /api/settings/file-encryption/enable` requires explicit loss-warning confirmation, enables encryption, persists the setting, encrypts managed uploads, and encrypts stored document text.
- `POST /api/settings/file-encryption/rotate` requires explicit rotation confirmation and rewrites encrypted managed files/document text with a new key.
- `backend/app/core/file_encryption.py` owns key resolution, file/text encryption, and decrypting read adapters.
- `backend/app/services/file_encryption_migration.py` owns migration and rotation across managed files and document rows.
- `backend/app/core/backup_manager.py` writes encrypted backup archives when file encryption is enabled and decrypts archives for verify/restore.

## Security Notes

- Preferred key storage is an operator secrets manager or macOS Keychain. Source installs may use the owner-only local fallback key file.
- Losing the key is destructive for encrypted uploads, document text, and encrypted backups.
- Linked external watch folders are not silently rewritten by Istara; the indexed/stored document text is encrypted, while the external original remains under the external folder owner's control.
- Auth and role scope stay strict: only global admins can enable or rotate encryption.

## Tests And Verification

- `tests/test_file_encryption.py`
- `tests/test_backup.py`
- `python scripts/security_benchmark.py --fail-on-threshold` is required for changes to this surface.

## When To Update

- Update this page whenever encryption key handling, backup encryption, upload/document read paths, admin settings UI, or related tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
