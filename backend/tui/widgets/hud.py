"""Hud — status line: run control state, clock, population, selection."""

from __future__ import annotations

from rich.text import Text

from textual.widget import Widget

from ..state import StateMessage
from .. import theme


class Hud(Widget):
    DEFAULT_CSS = """
    Hud { height: auto; padding: 0 1; background: #161b22; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._state: StateMessage | None = None
        self.paused = False
        self.speed = 10.0
        self.status = "connecting…"
        self.selected_line = ""

    def update_state(self, st: StateMessage | None) -> None:
        self._state = st
        self.refresh()

    def update_status(self, status: str, paused: bool, speed: float) -> None:
        self.status = status
        self.paused = paused
        self.speed = speed
        self.refresh()

    def update_selection(self, line: str) -> None:
        self.selected_line = line
        self.refresh()

    def render(self) -> Text:
        st = self._state
        text = Text()
        if st is None:
            text.append(f"◌ {self.status}", style="dim")
            return text
        play = "‖" if self.paused else "▶"
        text.append(f"{play} ", style="bold red" if self.paused else "bold green")
        text.append(f"tick {st.tick}", style="bold")
        text.append(" · ")
        text.append(f"alive {st.creatures_alive}", style="#3fb950")
        text.append(f" · dead {st.creatures_dead}", style="dim")
        if st.infected_count:
            text.append(f" · infected {st.infected_count}", style="#d29922")
        night = st.time_of_day < 0.2 or st.time_of_day > 0.8
        sky = "-" if night else "O"
        text.append(f" · {sky} day {st.day} {theme.SEASON_ICONS.get(st.season, '')}{st.season}")
        text.append(f" · {theme.WEATHER_ICONS.get(st.weather, '')} {st.weather}")
        if st.age:
            text.append(f" · age: {st.age}", style="magenta")
        # caste counts, colored
        castes = [
            (k, v)
            for k, v in sorted(st.population.items(), key=lambda kv: -kv[1])
            if k in theme.CASTE_COLORS or k in ("Food", "House", "Corpse")
        ]
        creature_chips = [c for c in castes if c[0] in theme.CASTE_COLORS]
        object_chips = [c for c in castes if c[0] not in theme.CASTE_COLORS]
        line2 = Text()
        for i, (k, v) in enumerate(creature_chips[:8]):
            if i:
                line2.append(" ")
            line2.append(f"{k} {v}", style=theme.caste_color(k))
        for k, v in object_chips:
            line2.append(f"  {k.lower()} {v}", style="dim")
        text.append("\n")
        text.append_text(line2)
        text.append(f"\n{self.status}", style="dim")
        if self.selected_line:
            text.append(f" · {self.selected_line}")
        return text
