"""Alembic environment configuration.

The database URL is resolved in this order:
1. An explicit ``sqlalchemy.url`` set on the ``Config`` object (e.g. by
   ``inv.storage.migrations.upgrade_to_head`` or by ``alembic -x url=...``).
2. The ``INVENTORY_DATABASE_URL`` env var (through ``inv.settings``).
3. ``Settings.db_path`` default (XDG data dir).

The ``[alembic].sqlalchemy.url`` value in ``alembic.ini`` is only used as a
last-resort placeholder when the environment carries no override; callers
should not rely on it.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from inv.settings import get_settings
from inv.storage.orm import Base

# this is the Alembic Config object, which provides access to the values
# within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# metadata for 'autogenerate' support
target_metadata = Base.metadata


def _resolve_url() -> str:
    """Pick the sqlalchemy.url that migrations should run against."""
    # Respect any URL the programmatic caller set; fall back to settings.
    configured = config.get_main_option("sqlalchemy.url")
    if configured and not configured.endswith("_alembic_placeholder.db"):
        return configured
    settings = get_settings()
    return f"sqlite:///{settings.db_path}"


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emits SQL, no DBAPI needed)."""
    context.configure(
        url=_resolve_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode using a live Engine."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _resolve_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.StaticPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
