"""PlotsPanel — god's foreshadowing: upcoming wars/schisms as progress bars."""

from __future__ import annotations

from rich.text import Text

from textual.widget import Widget

FULL = 10
BLOCKS = "░▒▓█"


def _bar(progress: float, width: int = FULL) -> str:
    filled = max(0, min(width, int(round(progress / 100 * width)))) if progress > 1 else max(0, min(width, int(progress)))
    return "#" * filled + "." * (width - filled)


class PlotsPanel(Widget):
    DEFAULT_CSS = """
    PlotsPanel { height: auto; padding: 0 1; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._plots: list[dict] = []

    def update_plots(self, plots: list[dict]) -> None:
        self._plots = plots or []
        self.refresh()

    def render(self) -> Text:
        text = Text()
        if not self._plots:
            text.append("no plots brewing — the clans are calm", style="dim")
            return text
        for i, pl in enumerate(self._plots):
            kind = pl.get("type", "?")
            icon = "war" if kind == "war" else "plot"
            prog = pl.get("progress") or 0
            mx = pl.get("max") or FULL
            frac = min(1.0, prog / mx) if mx else 0
            bar = _bar(frac * FULL)
            color = "#f85149" if kind == "war" else "#e3b341"
            text.append(f"{icon} ", style="bold " + color)
            text.append(f"{pl.get('a_name') or pl.get('a') or '?'}")
            text.append(" vs " if kind == "war" else " splits → ")
            text.append(f"{pl.get('b_name') or pl.get('b') or '?'} ")
            text.append(f"[{bar}] {prog}/{mx}", style=color)
            if i < len(self._plots) - 1:
                text.append("\n")
        return text


__all__ = ["PlotsPanel"]
