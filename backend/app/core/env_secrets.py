"""Canonical secret-key boundary shared by the env read and write sides.

This module is deliberately a LEAF: it imports nothing from the application,
so both ``app.config`` (read side — a runtime env file may not override these
keys when the process environment already sets them) and
``app.core.env_persistence`` (write side — these keys never land in a shared
env file) can depend on one definition without creating an import cycle
between configuration and persistence.
"""

# Server-auth and data-encryption secrets. The container/process environment is
# authoritative for every key listed here: a stale or shared env file must not
# be able to hijack them on restart, and rotating one through compose must
# never be a silent no-op.
SECRET_ENV_DENYLIST = frozenset(
    {
        "ADMIN_PASSWORD",
        "DATA_ENCRYPTION_KEY",
        "NETWORK_ACCESS_TOKEN",
        "JWT_SECRET",
    }
)
