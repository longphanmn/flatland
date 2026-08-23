"""CreatureInspector — live dossier modal for one creature."""

from __future__ import annotations

import asyncio
from typing import Any

from rich.text import Text

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, RichLog, Static

from .. import theme


def _bar(value: float, maximum: float, width: int = 24) -> str:
    frac = max(0.0, min(1.0, value / maximum if maximum else 0))
    filled = int(round(frac * width))
    return "[" + "#" * filled + "." * (width - filled) + "]"


class InspectorScreen(ModalScreen):
    BINDINGS = [("escape", "close", "Close")]

    DEFAULT_CSS = """
    InspectorScreen { align: center middle; background: #0d1117cc; }
    #inspector-box { width: 84; height: 80%; max-height: 34; border: round #30363d;
                     background: #161b22; padding: 0 1; }
    #inspector-head { height: auto; padding: 0 1; }
    #inspector-bars { height: auto; padding: 0 1; }
    #inspector-stats { height: auto; padding: 0 1; }
    #inspector-body { height: 1fr; }
    #inspector-family { height: 45%; border-top: solid #30363d; }
    #inspector-log { height: 1fr; border-top: solid #30363d; }
    .modal-actions { height: auto; align-horizontal: right; padding: 0 1; }
    """

    def __init__(self, creature_id: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self.creature_id = creature_id
        self._data: dict[str, Any] | None = None
        self._refresh_timer = None

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="inspector-box"):
            yield Static("loading…", id="inspector-head")
            yield Static("", id="inspector-bars")
            yield Static("", id="inspector-stats")
            with Horizontal(id="inspector-body"):
                pass
            yield DataTable(id="inspector-family")
            yield RichLog(id="inspector-log", markup=True, wrap=True, max_lines=120)
        with Horizontal(classes="modal-actions"):
            yield Button("Close", variant="primary", id="btn-insp-close")

    async def on_mount(self) -> None:
        table = self.query_one("#inspector-family", DataTable)
        table.cursor_type = "row"
        table.add_columns("relation", "who", "#id", "caste", "status")
        self.border_subtitle = f"creature #{self.creature_id}"
        self._refresh_timer = self.set_interval(1.0, self.refresh_data)
        await self.refresh_data()

    async def refresh_data(self) -> None:
        try:
            self._data = await self.app.rest.creature(self.creature_id)  # type: ignore[attr-defined]
        except Exception:
            return
        self._render_dossier()

    def _render_dossier(self) -> None:
        data = self._data
        if not data:
            return
        ent = data.get("entity") or {}
        head = self.query_one("#inspector-head", Static)
        bars = self.query_one("#inspector-bars", Static)
        stats = self.query_one("#inspector-stats", Static)

        name = ent.get("personal_name") or ent.get("caste") or f"#{self.creature_id}"
        glyph = ent.get("glyph") or ""
        color = ent.get("clan_color") or theme.caste_color(ent.get("caste"))
        clan = ent.get("clan_name") or ""
        line = Text()
        line.append(f"{name} ", style=f"bold {color}")
        line.append(f"{glyph} ", style=color)
        line.append(f"#{self.creature_id}", style="dim")
        caste = ent.get("caste")
        if caste:
            line.append(f" · {caste}", style=theme.caste_color(caste))
        sex = ent.get("sex")
        if sex:
            line.append(f" · {'female' if sex == 'female' else 'male'}")
        if clan:
            line.append(f" · clan {clan}", style="dim")
        gen = ent.get("generation")
        if gen is not None:
            line.append(f" · gen {gen}", style="dim")
        if not data.get("entity"):
            line.append("  † deceased", style="bold #f85149")
        head.update(line)

        energy = ent.get("energy")
        health = ent.get("health")
        btxt = Text()
        emax = 100.0
        if isinstance(energy, (int, float)):
            status = ent.get("status") or ""
            scolor = theme.STATUS_COLORS.get(status, "#3fb950")
            btxt.append("energy ")
            btxt.append(_bar(energy, emax), style=scolor)
            btxt.append(f" {round(energy)}\n", style="dim")
        if isinstance(health, (int, float)):
            hcolor = "#3fb950" if health > 60 else ("#d29922" if health > 25 else "#f85149")
            btxt.append("health ")
            btxt.append(_bar(health, 100), style=hcolor)
            btxt.append(f" {round(health)}\n", style="dim")
        chill = ent.get("chill")
        if isinstance(chill, (int, float)) and chill > 0:
            btxt.append("chill  ")
            btxt.append(_bar(chill, 12), style="#79c0ff")
            btxt.append(f" {round(chill)}\n", style="dim")
        bars.update(btxt)

        stxt = Text()
        chips = []
        if ent.get("status"):
            chips.append((ent["status"], theme.STATUS_COLORS.get(ent["status"], "dim")))
        if ent.get("infected"):
            chips.append(("sick", "#3fb950"))
        if ent.get("sleeping"):
            chips.append(("asleep", "#79c0ff"))
        for word, col in chips:
            stxt.append(f"{word} ", style=col)
        bits = []
        if ent.get("stage"):
            bits.append(str(ent["stage"]))
        age = ent.get("age")
        lifespan = ent.get("lifespan")
        if age is not None:
            bits.append(f"age {age}" + (f"/{round(lifespan)}" if lifespan else ""))
        if ent.get("meals") is not None:
            bits.append(f"meals {ent['meals']}")
        if ent.get("trait"):
            bits.append(f"trait {ent['trait']}")
        irr = ent.get("irregularity")
        if isinstance(irr, (int, float)) and irr > 0:
            bits.append(f"irr {irr:.2f}")
        if ent.get("is_predator"):
            bits.append("carnivore")
        if ent.get("is_herbivore"):
            bits.append("herbivore beast")
        born = ent.get("born_tick")
        if born is not None:
            bits.append(f"born tick {born}")
        stxt.append(" · ".join(bits), style="dim")
        stats.update(stxt)

        family = data.get("family") or {}
        table = self.query_one("#inspector-family", DataTable)
        table.clear()
        for relation, card in (("mother", family.get("mother")), ("father", family.get("father"))):
            if card:
                self._add_kin(table, relation, card)
        for card in family.get("children") or []:
            self._add_kin(table, "child", card)

        log = self.query_one("#inspector-log", RichLog)
        events = (data.get("events") or [])[-40:]
        if events:
            log.clear()
            from ..state import HistoryEvent
            from ..widgets.chronicle import format_event

            for d in reversed(events):
                log.write(format_event(HistoryEvent.from_dict(d)))

    def _add_kin(self, table: DataTable, relation: str, card: dict) -> None:
        alive = card.get("alive", True)
        who = Text(
            f"{card.get('personal_name') or '?'} {card.get('glyph') or ''}".strip(),
            style="" if alive else "dim strike",
        )
        mark = "† " if not alive else ""
        table.add_row(
            Text(relation + (mark if not alive else ""), style="dim" if not alive else ""),
            who,
            str(card.get("id")),
            card.get("caste") or "-",
            "alive" if alive else "dead",
            key=str(card.get("id")),
        )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        try:
            cid = int(str(event.row_key.value))
        except (TypeError, ValueError):
            return
        self.dismiss()
        self.app.show_inspector(cid)  # type: ignore[attr-defined]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-insp-close":
            self.dismiss()

    def action_close(self) -> None:
        self.dismiss()
