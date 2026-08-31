"""Shared test setup: keep the app's SQLite database out of the repo."""

import os
import tempfile

os.environ["FLATWORLD_DB"] = os.path.join(
    tempfile.mkdtemp(prefix="flatworld_test_"), "test_flatland.db"
)
# Deterministic god passkey so tests may touch laws/control via X-God-Key.
os.environ["FLATWORLD_GOD_KEY"] = "test-key"
# Disable new soft-cap/safeguard engines for deterministic tests (they are integration-tested separately)
os.environ["FLATWORLD_SOFT_CAP_ENABLED"] = "false"
os.environ["FLATWORLD_SAFEGUARD_ENABLED"] = "false"
os.environ["FLATWORLD_MORPHOLOGY_ANNEALING_ENABLED"] = "false"
# Patch Config defaults for tests that construct Config directly
try:
    from app.config import Config as _Cfg
    _Cfg.__dataclass_fields__["soft_cap_enabled"].default = False
    _Cfg.__dataclass_fields__["safeguard_enabled"].default = False
    _Cfg.__dataclass_fields__["morphology_annealing_enabled"].default = False
    # also patch the class attribute for direct instantiation without from_env
    _Cfg.soft_cap_enabled = False  # type: ignore
    _Cfg.safeguard_enabled = False  # type: ignore
    _Cfg.morphology_annealing_enabled = False  # type: ignore
except Exception:
    pass
