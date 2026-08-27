"""ClanDetails — roster, war record and chronicle of one clan."""

from __future__ import annotations

from typing import Any

from rich.text import Text

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, RichLog, Static

from .. import theme


class ClanDetailsScreen(ModalScreen):
    BINDINGS = [("escape", "close", "Close")]

    DEFAULT_CSS = """
    ClanDetailsScreen { align: center middle; background: #0d1117cc; }
    #clan-box { width: 84; height: 80%; max-height: 34; border: round #30363d;
                background: #161b22; padding: 0 1; }
    #clan-head { height: auto; padding: 0 1; }
    #clan-members { height: 55%; }
    #clan-log { height: 1fr; border-top: solid #30363d; }
    .modal-actions { height: auto; align-horizontal: right; padding: 0 1; }
    """

    def __init__(self, clan_id: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self.clan_id = clan_id
        self._data: dict[str, Any] | None = None

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="clan-box"):
            yield Static("loading…", id="clan-head")
            yield DataTable(id="clan-members")
            yield RichLog(id="clan-log", markup=True, wrap=True, max_lines=100)
        with Horizontal(classes="modal-actions"):
            yield Button("Close", variant="primary", id="btn-clan-close")

    async def on_mount(self) -> None:
        table = self.query_one("#clan-members", DataTable)
        table.cursor_type = "row"
        table.add_columns("#id", "who", "caste", "personality", "item", "energy", "status")
        try:
            self._data = await self.app.rest.clan(self.clan_id)  # type: ignore[attr-defined]
        except Exception:
            self._data = None
        self._render_dossier()

    def _render_dossier(self) -> None:
        data = self._data
        if not data:
            self.query_one("#clan-head", Static).update(f"clan #{self.clan_id} not found")
            return
        color = data.get("color") or "#8b949e"
        head = Text()
        head.append(str(data.get("name") or f"Clan {self.clan_id}"), style=f"bold {color}")
        totem = data.get("totem")
        if totem:
            head.append(f" · {theme.TOTEM_ICONS.get(totem, totem)}", style=f"bold {color}")
        founded_day = data.get("founded_day", (data.get("born_tick", 0) or 0) // 1200)
        dead_count = data.get("dead_count", 0)
        head.append(f" · 🌱 Day {founded_day}", style="#3fb950")
        head.append(f" · 💀 {dead_count} dead", style="#ff7b72")
        head.append(
            f" · pop {data.get('population', 0)} · wars {data.get('war_wins', 0)}W/"
            f"{data.get('war_losses', 0)}L",
            style="dim",
        )
        larder = data.get("larder")
        if larder is not None:
            head.append(f" · 🥖 larder {round(larder)}", style="#f4a261")
        sp = data.get("specialization")
        if isinstance(sp, dict):
            parts = []
            for key in ("warrior", "farmer", "scavenger", "builder"):
                v = sp.get(key)
                if v is not None:
                    parts.append(f"{key} {v:.2f}")
            if parts:
                head.append(f"\n{' · '.join(parts)}", style="dim")
        cult = data.get("culture")
        if cult:
            head.append(f" · culture {cult}", style="#bc8cff")
        houses = data.get("houses") or ([data["house"]] if data.get("house") else [])
        if houses:
            active_h = [h for h in houses if not h.get("is_ruin")]
            if active_h:
                main_h = next((h for h in active_h if h.get("is_main")), active_h[0])
                head.append(f" · 👑 main ({round(main_h['x'])},{round(main_h['y'])})", style="#ffd166")
                if len(active_h) > 1:
                    head.append(f" (+{len(active_h)-1} houses)", style="dim")
        leader = data.get("leader_id")
        if leader:
            head.append(f" · 👑 leader #{leader}", style="bold #e3b341")
        self.query_one("#clan-head", Static).update(head)

        table = self.query_one("#clan-members", DataTable)
        table.clear()
        for m in data.get("members") or []:
            name = m.get("personal_name") or ""
            title = m.get("title") or ""
            glyph = m.get("glyph") or ""
            full_name = f"{name} {title} {glyph}".strip() or f"#{m.get('id')}"
            who = Text(full_name, style=theme.caste_color(m.get("caste")))
            pers = m.get("personality") or m.get("trait") or "-"
            pers_label = theme.PERSONALITY_ICONS.get(pers, pers)
            item = m.get("equipped_item") or ""
            fb = m.get("food_basket", 0)
            if item == "basket" or fb > 0:
                item_label = f"🧺 {fb}/3"
            elif item:
                item_label = theme.ITEM_ICONS.get(item, item)
            else:
                item_label = "-"
            energy_val = m.get("energy")
            energy_str = f"{round(energy_val)}" if isinstance(energy_val, (int, float)) else "-"
            table.add_row(
                str(m.get("id")),
                who,
                m.get("caste") or "-",
                pers_label,
                item_label,
                energy_str,
                m.get("status") or "",
                key=str(m.get("id")),
            )

        log = self.query_one("#clan-log", RichLog)
        from ..state import HistoryEvent
        from ..widgets.chronicle import format_event

        events = (data.get("events") or [])[-40:]
        for d in reversed(events):
            log.write(format_event(HistoryEvent.from_dict(d)))

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        try:
            cid = int(str(event.row_key.value))
        except (TypeError, ValueError):
            return
        self.dismiss()
        self.app.show_inspector(cid)  # type: ignore[attr-defined]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-clan-close":
            self.dismiss()

    def action_close(self) -> None:
        self.dismiss()
