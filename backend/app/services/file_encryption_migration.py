"""Migration helpers for managed file and document-text encryption."""

from sqlalchemy import select

from app.core.file_encryption import (
    CRYPTO_AVAILABLE,
    TEXT_PREFIX,
    Fernet,
    encrypt_file_in_place,
    encrypt_text_value,
    is_encrypted_file,
    key_fingerprint,
    managed_upload_files,
    replace_file_encryption_key,
    resolve_file_encryption_key,
    rewrite_encrypted_file,
    rewrite_encrypted_text,
)
from app.models.document import Document


async def encrypt_existing_project_content(db) -> dict[str, int | str]:
    """Encrypt existing managed upload files and document text fields."""
    resolve_file_encryption_key(create=True)
    files_encrypted = 0
    for path in managed_upload_files():
        if encrypt_file_in_place(path, force=True):
            files_encrypted += 1

    docs_updated = 0
    docs = (await db.execute(select(Document))).scalars().all()
    for doc in docs:
        changed = False
        if doc.content_text and not doc.content_text.startswith(TEXT_PREFIX):
            doc.content_text = encrypt_text_value(doc.content_text)
            changed = True
        if doc.content_preview and not doc.content_preview.startswith(TEXT_PREFIX):
            doc.content_preview = encrypt_text_value(doc.content_preview)
            changed = True
        if changed:
            docs_updated += 1
    if docs_updated:
        await db.commit()
    return {
        "files_encrypted": files_encrypted,
        "documents_encrypted": docs_updated,
        "key_fingerprint": key_fingerprint(),
    }


async def rotate_existing_project_content(db) -> dict[str, int | str]:
    """Rotate the active file-encryption key and re-encrypt protected content."""
    if not CRYPTO_AVAILABLE:
        raise RuntimeError("cryptography is required for file encryption")
    old_key = resolve_file_encryption_key(create=False)
    if not old_key:
        raise RuntimeError("existing file encryption key is not available")
    new_key = Fernet.generate_key().decode()

    files_rotated = 0
    for path in managed_upload_files():
        if is_encrypted_file(path):
            rewrite_encrypted_file(path, old_key=old_key, new_key=new_key)
            files_rotated += 1

    docs_rotated = 0
    docs = (await db.execute(select(Document))).scalars().all()
    for doc in docs:
        changed = False
        if doc.content_text:
            doc.content_text = rewrite_encrypted_text(doc.content_text, old_key=old_key, new_key=new_key)
            changed = True
        if doc.content_preview:
            doc.content_preview = rewrite_encrypted_text(
                doc.content_preview,
                old_key=old_key,
                new_key=new_key,
            )
            changed = True
        if changed:
            docs_rotated += 1

    replace_file_encryption_key(new_key)
    if docs_rotated:
        await db.commit()
    return {
        "files_rotated": files_rotated,
        "documents_rotated": docs_rotated,
        "key_fingerprint": key_fingerprint(new_key),
    }
