"""Overview — population sparkline, caste chips, trophic line, run selector."""

from __future__ import annotations

from rich.text import Text

from textual.widgets import Static

from ..state import StateMessage
from .. import theme

SPARK = "▁▂▃▄▅▆▇█"


def _sparkline(values: list[int]) -> str:
    if not values:
        return ""
    lo, hi = min(values), max(values)
    span = max(hi - lo, 1)
    return "".join(SPARK[min(int((v - lo) * 8 / span), 7)] for v in values)


class Overview(Static):
    """Population history + trophic counts + recent runs."""

    DEFAULT_CSS = """
    Overview { height: auto; padding: 0 1; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._hist: list[int] = []
        self._state: StateMessage | None = None
        self._worlds: list[dict] = []

    def update_state(self, st: StateMessage) -> None:
        self._state = st
        if st.tick == 0 or (self._hist and st.tick < self._hist[-1]):
            self._hist = []
        self._hist.append(st.creatures_alive)
        self._hist = self._hist[-60:]
        self.refresh()

    def update_worlds(self, worlds: list[dict]) -> None:
        self._worlds = worlds
        self.refresh()

    def render(self) -> Text:
        st = self._state
        text = Text()
        text.append("population\n", style="bold #8b949e")
        text.append(_sparkline(self._hist) or "…", style="#3fb950")
        if self._hist:
            text.append(f" {self._hist[-1]} alive", style="bold")
        if st:
            pop = st.population or {}
            herb = sum(v for k, v in pop.items() if k.lower().startswith("herbivore"))
            pred = sum(v for k, v in pop.items() if k.lower().startswith("predator"))
            food = sum(v for k, v in pop.items() if k.lower() == "food")
            corpse = sum(v for k, v in pop.items() if k.lower() == "corpse")
            houses = sum(v for k, v in pop.items() if k.lower() == "house")
            text.append(f"\nfood {food} · herb {herb} · pred {pred}", style="dim")
            text.append(f" · corpses {corpse} · houses {houses}\n", style="dim")
            causes = sorted(st.dead_by_cause.items(), key=lambda kv: -kv[1])
            if causes:
                text.append("dead: ", style="dim")
                text.append(
                    " ".join(f"{k} {v}" for k, v in causes[:6]),
                    style="dim",
                )
        if self._worlds:
            text.append("\n\nruns\n", style="bold #8b949e")
            for w in self._worlds[:5]:
                ended = "live" if not w.get("ended_at") else f"ended {str(w.get('ended_at'))[:16]}"
                cur = ""
                if st and w.get("seed") == st.seed and not w.get("ended_at"):
                    cur = " ←"
                text.append(
                    f" #{w.get('id')} seed {w.get('seed')} {ended}{cur}\n",
                    style="green" if cur else "dim",
                )
        return text


__all__ = ["Overview"]
