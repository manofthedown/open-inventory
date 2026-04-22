"""Programmatic Alembic runner.

The app always migrates its own SQLite DB on startup (via ``inventory init``
and in tests), so every environment has a matching ``alembic_version`` row
and schema drift is impossible. This module centralises the Alembic
configuration plumbing so callers don't need to know about ini files.
"""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config

from alembic import command
from inv.settings import Settings

# The alembic/ directory and alembic.ini live inside the inv/ package so
# they are included in the installed wheel and available at runtime
# regardless of whether the package is run from a source checkout or from
# a pipx/Docker install.  _INV_PKG_ROOT resolves to the inv/ directory
# whether running from source (inv/storage/migrations.py → inv/) or from
# an installed wheel (site-packages/inv/storage/migrations.py → inv/).
_INV_PKG_ROOT = Path(__file__).resolve().parent.parent  # inv/
_ALEMBIC_INI = _INV_PKG_ROOT / "alembic.ini"
_ALEMBIC_SCRIPT_LOCATION = _INV_PKG_ROOT / "alembic"


def _build_config(settings: Settings) -> Config:
    """Build an Alembic ``Config`` pointed at the settings-derived DB URL."""
    cfg = Config(str(_ALEMBIC_INI))
    # Alembic's script_location is relative to the ini file by default; we set
    # it explicitly so this works whether the package is run from a source
    # checkout or from an installed wheel (which still ships alembic/).
    cfg.set_main_option("script_location", str(_ALEMBIC_SCRIPT_LOCATION))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{settings.db_path}")
    return cfg


def upgrade_to_head(settings: Settings) -> None:
    """Run ``alembic upgrade head`` against the settings-derived database."""
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    cfg = _build_config(settings)
    command.upgrade(cfg, "head")


def downgrade_to_base(settings: Settings) -> None:
    """Run ``alembic downgrade base``. Primarily used by the test suite."""
    cfg = _build_config(settings)
    command.downgrade(cfg, "base")
