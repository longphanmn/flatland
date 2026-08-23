"""Chronicle — color-coded RichLog of world events (live feed + pagination)."""

from __future__ import annotations

from rich.text import Text

from textual.widgets import RichLog

from ..state import HistoryEvent, StateMessage
from .. import theme

MAX_LOG = 400


class Chronicle(RichLog):
    DEFAULT_CSS = """
    Chronicle { border-title-color: #8b949e; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(markup=True, highlight=False, wrap=True, max_lines=MAX_LOG, **kwargs)
        self._seen: set[tuple] = set()

    def on_mount(self) -> None:
        self.border_title = "Chronicle"

    def clear_events(self) -> None:
        self._seen.clear()
        self.clear()

    def add_from_state(self, st: StateMessage) -> None:
        fresh = [ev for ev in st.events if ev.key not in self._seen]
        for ev in fresh:
            self._seen.add(ev.key)
        for ev in reversed(fresh):  # newest at the bottom; log scrolls
            self.write(format_event(ev, st.clans))

    def add_fetched(self, events: list[dict], clans: dict | None = None) -> None:
        """Older events from GET /api/history (already oldest-first)."""
        for d in events:
            ev = HistoryEvent.from_dict(d)
            if ev.key in self._seen:
                continue
            self._seen.add(ev.key)
            self.write(format_event(ev, clans or {}))


def _clan_label(clans: dict, cid) -> str:
    try:
        info = clans.get(str(cid)) or {}
        name = info.get("name")
        if name:
            return f"{name} ({cid})"
    except Exception:
        pass
    return f"#{cid}"


def format_event(ev: HistoryEvent, clans: dict | None = None) -> Text:
    clans = clans or {}
    p = ev.payload or {}
    who = p.get("personal_name") or ev.caste or ""
    glyph = p.get("glyph") or ""
    mark = f"{who} {glyph}".strip() or f"#{ev.entity_id}"
    line = Text()
    color = theme.EVENT_COLORS.get(ev.type, "#8b949e")
    t = ev.type

    if t == "birth":
        line.append(f"{mark}", style="bold " + color)
        line.append(f" #{ev.entity_id} born to #{p.get('mother')} × #{p.get('father')}")
        line.append(f" gen {p.get('generation', '?')}", style="dim")
    elif t == "promotion":
        line.append(f"{mark} ", style=color)
        line.append(f"rose {p.get('from', 'Soldier')} → {p.get('to', ev.caste)}", style=color)
    elif t == "demotion":
        line.append(f"{mark} judged irregular and demoted", style=color)
    elif t == "predation":
        line.append(f"{mark} predated ", style=color)
        line.append(f"{p.get('prey_caste')} #{p.get('prey')}")
    elif t == "war":
        line.append(f"{mark} fell in clan war", style="bold " + color)
        if p.get("winner"):
            line.append(f" — winner #{p.get('winner')}", style="dim")
    elif t in ("alliance", "rivalry"):
        line.append(
            f"clans {_clan_label(clans, p.get('a'))} & {_clan_label(clans, p.get('b'))} {t}",
            style=color,
        )
        if p.get("score") is not None:
            line.append(f" (score {p.get('score')})", style="dim")
    elif t == "schism":
        line.append(f"schism: ", style=color)
        line.append(str(p.get("parent_name") or _clan_label(clans, p.get("parent"))))
        line.append(" → ")
        line.append(str(p.get("new_name") or _clan_label(clans, p.get("new_clan"))), style="bold " + color)
        members = p.get("members") or []
        line.append(f" ({len(members)} broke away)", style="dim")
    elif t == "conquest":
        line.append("conquest: ", style=color)
        line.append(_clan_label(clans, p.get("winner_clan")))
        line.append(f" seized house {p.get('house_id')} from ")
        line.append(_clan_label(clans, p.get("loser_clan")))
    elif t == "succession":
        line.append(f"succession in ", style=color)
        line.append(_clan_label(clans, p.get("clan_id")))
        line.append(f": #{p.get('new_leader')} succeeds #{p.get('prev_leader')}", style="dim")
    elif t == "settlement":
        line.append("settlement founded", style=color)
        if p.get("clan_id"):
            line.append(f" by {_clan_label(clans, p.get('clan_id'))}", style="dim")
    elif t == "fire":
        line.append(f"fire {p.get('kind') or ''} at ({round(ev.x)}, {round(ev.y)})", style=color)
    elif t == "disaster":
        line.append(f"disaster {p.get('kind')} r{p.get('r', '')} at ({round(ev.x)}, {round(ev.y)})", style=color)
    elif t == "outbreak":
        line.append(f"{mark} outbreak", style=color)
    elif t == "recovery":
        line.append(f"{mark} recovered", style=color)
    else:
        # death and anything unlisted
        cause = f" of {ev.cause}" if ev.cause else ""
        label = {"death": "died"}.get(t, t)
        line.append(f"{mark} #{ev.entity_id} {label}{cause}", style=color)

    line.append(f"  ·{ev.tick}", style="dim")
    return line
