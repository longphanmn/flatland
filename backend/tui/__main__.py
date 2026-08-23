"""Run the TUI: `uv run -m tui` (env FLATWORLD_WS, default ws://localhost:8000/ws)."""

import os

from .app import FlatlandApp


def main() -> None:
    ws_url = os.environ.get("FLATWORLD_WS", "ws://localhost:8000/ws")
    FlatlandApp(ws_url=ws_url).run()


if __name__ == "__main__":
    main()
