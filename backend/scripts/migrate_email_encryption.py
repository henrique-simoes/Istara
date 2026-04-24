"""Migration script: encrypt existing user emails and populate email_hash.

Run this once after deploying the email encryption changes.
It is safe to run multiple times (idempotent).
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.core.field_encryption import hash_field
from app.models.database import async_session
from app.models.user import User


async def migrate():
    async with async_session() as db:
        result = await db.execute(select(User))
        users = result.scalars().all()

        migrated = 0
        skipped = 0
        for user in users:
            # If email is already encrypted (has ENC: prefix), skip
            if user.email and user.email.startswith("ENC:"):
                # Just ensure email_hash is populated
                if not user.email_hash:
                    decrypted = user.email  # EncryptedType will decrypt on access
                    user.email_hash = hash_field(decrypted)
                    migrated += 1
                else:
                    skipped += 1
                continue

            # Plaintext email — assign through EncryptedType so it encrypts once on bind.
            plaintext = user.email or ""
            user.email = plaintext
            user.email_hash = hash_field(plaintext)
            migrated += 1

        await db.commit()
        print(f"Migration complete: {migrated} users updated, {skipped} already encrypted.")


if __name__ == "__main__":
    asyncio.run(migrate())
