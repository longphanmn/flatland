"""Shared test setup: keep the app's SQLite database out of the repo."""

import os
import tempfile

os.environ["FLATWORLD_DB"] = os.path.join(
    tempfile.mkdtemp(prefix="flatworld_test_"), "test_flatland.db"
)
# Deterministic god passkey so tests may touch laws/control via X-God-Key.
os.environ["FLATWORLD_GOD_KEY"] = "test-key"
