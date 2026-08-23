"""ClanPanel — DataTable roster of clans (REST /api/clans, polled)."""

from __future__ import annotations

from typing import Any

from rich.text import Text

from textual.widgets import DataTable


class ClanPanel(DataTable):
    DEFAULT_CSS = """
    ClanPanel { height: 1fr; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.cursor_type = "row"
        self._rows: dict[int, int] = {}  # clan_id -> row index

    def on_mount(self) -> None:
        self.add_columns("clan", "pop", "totem", "wars", "settled")
        self.border_title = "Clans"

    def update_clans(self, clans: list[dict[str, Any]]) -> None:
        self.clear()
        self._rows.clear()
        for c in clans:
            if not c.get("population", 0):
                continue  # extinct clans stay in the chronicle, not on the board
            name = Text(f"{c.get('name') or 'Clan ?'}", style=c.get("color") or "#8b949e")
            totem = str(c.get("totem") or "-")
            wars = f"{c.get('war_wins', 0)}W/{c.get('war_losses', 0)}L"
            house = c.get("house")
            settled = "-" if not house else ("ruin" if house.get("is_ruin") else f"({round(house['x'])},{round(house['y'])})")
            key = str(c["id"])
            self.add_row(
                name,
                str(c.get("population", 0)),
                totem,
                wars,
                settled,
                key=key,
            )
            self._rows[int(c["id"])] = self.row_count - 1

    @property
    def selected_clan_id(self) -> int | None:
        if self.row_count == 0:
            return None
        row = self.cursor_row
        for cid, idx in self._rows.items():
            if idx == row:
                return cid
        return None


__all__ = ["ClanPanel"]
