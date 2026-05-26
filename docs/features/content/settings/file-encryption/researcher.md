---
stable_id: settings.file-encryption
title: File And Backup Encryption
ui_path: Settings > File And Backup Encryption
audience: researcher
status: documented
related_features: ["settings.users", "settings.security-factors", "documents.upload"]
related_glossary: []
code_references: ["frontend/src/components/settings/FileEncryptionManager.tsx", "backend/app/core/file_encryption.py", "backend/app/services/file_encryption_migration.py", "backend/app/api/routes/settings.py", "backend/app/api/routes/files.py", "backend/app/api/routes/documents.py", "backend/app/core/backup_manager.py"]
api_references: ["backend/app/api/routes/settings.py", "backend/app/api/routes/backup.py"]
test_references: ["tests/test_file_encryption.py", "tests/test_backup.py"]
last_verified: 2026-05-22
compass: CF-SPEC-134 / CF-1671
---

# File And Backup Encryption

## What It Does

Admins can turn on encryption for managed uploads, stored document text, and future backup archives. Existing managed project content is migrated when the feature is enabled.

## How Researchers Experience It

- Normal document upload, preview, reprocess, and report workflows keep working after encryption is enabled.
- File previews and media serving decrypt only after the normal project authorization check.
- Backups created after encryption is enabled download as encrypted `.tar.gz.enc` files.

## Admin Warnings

- Save the file-encryption key outside Istara. Losing it means encrypted files and backups cannot be restored.
- Rotate the key only after verifying a current backup and key custody path.
- External linked folders remain external; Istara encrypts stored/indexed document text, but does not silently rewrite originals outside its managed upload folder.

## Expected Outcomes

- Existing managed uploads and stored document content are encrypted when enabled.
- New uploads and document text are stored encrypted.
- Backup verify and restore require the correct key for encrypted archives.

## Evidence

- Source files: `frontend/src/components/settings/FileEncryptionManager.tsx`, `backend/app/core/file_encryption.py`, `backend/app/core/backup_manager.py`
- API references: `backend/app/api/routes/settings.py`, `backend/app/api/routes/backup.py`
- Tests: `tests/test_file_encryption.py`, `tests/test_backup.py`
