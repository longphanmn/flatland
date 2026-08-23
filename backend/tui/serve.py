"""Entry point for optional browser serving: `uv run textual serve -m tui.serve`.

Exposes a module-level App instance as `textual serve -m <module>` expects.
"""

import os

from .app import FlatlandApp

app = FlatlandApp(ws_url=os.environ.get("FLATWORLD_WS", "ws://localhost:8000/ws"))
