"""FlatlandApp — terminal frontend: reactive state, keybindings, WS lifecycle."""

from __future__ import annotations

from typing import Any

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Tab, Tabs

from . import theme
from .client import RESTClient, WSClient, http_base_for
from .state import HelloMessage, StateMessage
from .widgets import Chronicle, ClanPanel, Hud, Overview, WorldView
from .screens import ClanDetailsScreen, GodLawsScreen, HelpScreen, InspectorScreen

SPEED_PRESETS = [0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 60.0, 120.0]


POLL_CLANS = 3.0
POLL_WORLDS = 30.0


class FlatlandApp(App):
    TITLE = "Flatland"
    SUB_TITLE = "a god sets laws; the world emerges"
    CSS_PATH = "flatland.tcss"

    BINDINGS = [
        ("space", "toggle_pause", "Pause"),
        ("s", "step", "Step"),
        ("r", "reset", "Reset"),
        ("f", "fit_view", "Fit"),
        ("w", "toggle_follow", "Follow"),
        ("t", "cycle_chronicle_filter", "Log Filter"),
        ("a", "toggle_ascii", "ASCII/blocks"),
        ("plus", "zoom_in", "Zoom in"),
        ("equals_sign", "zoom_in", "Zoom in"),
        ("minus", "zoom_out", "Zoom out"),
        ("underscore", "zoom_out", "Zoom out"),
        ("h", "pan_left", "Pan ←"),
        ("l", "pan_right", "Pan →"),
        ("k", "pan_up", "Pan ↑"),
        ("j", "pan_down", "Pan ↓"),
        ("left", "pan_left", None),
        ("right", "pan_right", None),
        ("up", "pan_up", None),
        ("down", "pan_down", None),
        ("enter", "inspect", "Inspect"),
        ("i", "inspect", "Inspect"),
        ("c", "clan_of_selection", "Clan"),
        ("g", "laws", "God laws"),
        ("o", "load_older", "Older events"),
        ("question_mark", "help", "Help"),
        ("1", "speed(0)", "0.5×"),
        ("2", "speed(1)", "1×"),
        ("3", "speed(2)", "2×"),
        ("4", "speed(3)", "4×"),
        ("5", "speed(4)", "8×"),
        ("6", "speed(5)", "16×"),
        ("7", "speed(6)", "32×"),
        ("8", "speed(7)", "60×"),
        ("9", "speed(8)", "120×"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, ws_url: str = "ws://localhost:8000/ws", **kwargs) -> None:
        super().__init__(**kwargs)
        self.ws_url = ws_url
        self.rest = RESTClient(http_base_for(ws_url))
        self.world_state: StateMessage | None = None
        self.hello: HelloMessage | None = None
        self.paused = False
        self.speed = 10.0
        self.selected_id: int | None = None
        self._ws: WSClient | None = None
        self._prev_tick: int | None = None

    # ------------------------------------------------------------ layout
    # tab id → pane widget id (all panes stay mounted; Tabs only toggles)
    PANES = [
        ("tab-overview", "overview"),
        ("tab-chronicle", "chronicle"),
        ("tab-clans", "clans-table"),
    ]

    def compose(self) -> ComposeResult:
        with Horizontal(id="main"):
            with Vertical(id="world-col"):
                yield Hud(id="hud")
                yield WorldView(id="world")
            with Vertical(id="side"):
                yield Tabs(
                    Tab("Overview", id="tab-overview"),
                    Tab("Chronicle", id="tab-chronicle"),
                    Tab("Clans", id="tab-clans"),
                )
                yield Overview(id="overview")
                yield Chronicle(id="chronicle")
                yield ClanPanel(id="clans-table")
        yield Footer()

    async def on_mount(self) -> None:
        self.query_one(Tabs).active = "tab-overview"
        self._show_pane("tab-overview")
        self._ws = WSClient(
            url=self.ws_url,
            on_hello=self._on_hello,
            on_state=self._on_state,
            on_status=self._on_status,
        )
        self._ws.start()
        self.set_interval(POLL_CLANS, self.poll_clans)
        self.set_interval(POLL_WORLDS, self.poll_worlds)
        self.call_later(self.poll_worlds)

    async def on_unmount(self) -> None:
        if self._ws is not None:
            await self._ws.stop()
        await self.rest.aclose()

    # ------------------------------------------------------- ws callbacks
    def _on_hello(self, hello: HelloMessage) -> None:
        self.hello = hello
        self.speed = hello.tick_rate
        self.call_later(self._refresh_hud)

    def _on_state(self, st: StateMessage) -> None:
        if self._prev_tick is not None and st.tick < self._prev_tick:
            # new world (reset): clear chronicle + sparkline
            self.query_one("#chronicle", Chronicle).clear_events()
        self._prev_tick = st.tick
        self.world_state = st
        self.query_one("#world", WorldView).set_state(st)
        self.query_one("#hud", Hud).update_state(st)
        self.query_one("#overview", Overview).update_state(st)
        chron = self.query_one("#chronicle", Chronicle)
        chron.add_from_state(st)
        self.call_later(self._sync_selection)

    def _on_status(self, status: str) -> None:
        hud = self.query_one("#hud", Hud)
        hud.update_status(status, self.paused, self.speed)

    def _refresh_hud(self) -> None:
        self.query_one("#hud", Hud).update_status(self._status_text(), self.paused, self.speed)

    def _status_text(self) -> str:
        base = f"ws {'●' if self._ws and self._ws.connected else '○'} {self.ws_url}"
        return base

    def _sync_selection(self) -> None:
        """Keep HUD selection line in step with the latest snapshot."""
        view = self.query_one("#world", WorldView)
        view.selected_id = self.selected_id
        if self.selected_id is None:
            view.select_entity(None)
            self.query_one("#hud", Hud).update_selection("")
            return
        ent = next(
            (
                e
                for e in (self.world_state.entities if self.world_state else [])
                if e.id == self.selected_id and e.kind == "creature"
            ),
            None,
        )
        view.select_entity(ent)
        if ent is not None:
            name = ent.personal_name or ent.caste or ""
            title = f" {ent.title}" if ent.title else ""
            clan = f" · clan {ent.clan_name}" if ent.clan_name else ""
            pers = f" · {theme.PERSONALITY_ICONS.get(ent.personality, ent.personality)}" if ent.personality else ""
            tool = f" · {theme.ITEM_ICONS.get(ent.equipped_item, ent.equipped_item)}" if ent.equipped_item else ""
            if ent.food_basket > 0:
                tool += f" 🧺[{ent.food_basket}/3]"
            status = f" · {ent.status}" if ent.status else ""
            line = f"selected {name}{title} #{ent.id} ({ent.caste}{clan}{pers}{tool}{status})"
        else:
            line = f"selected #{self.selected_id} — fallen"
        self.query_one("#hud", Hud).update_selection(line)

    def _show_pane(self, tab_id: str | None) -> None:
        for tab_id_, widget_id in self.PANES:
            pane = self.query_one(f"#{widget_id}")
            pane.display = tab_id_ == tab_id

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        self._show_pane(event.tab.id if event.tab else None)

    # ---------------------------------------------------------- polling
    async def poll_clans(self) -> None:
        try:
            data = await self.rest.clans()
        except Exception:
            return
        clans = data.get("clans") or []
        table = self.query_one("#clans-table", ClanPanel)
        table.update_clans(clans)
        if self.world_state is not None:
            self.world_state.clans = {
                str(c["id"]): {
                    "name": c.get("name"),
                    "color": c.get("color"),
                    "founder_id": c.get("founder_id"),
                    "born_tick": c.get("born_tick"),
                }
                for c in clans
            }

    async def poll_worlds(self) -> None:
        try:
            data = await self.rest.worlds()
        except Exception:
            return
        worlds = data.get("worlds") or []
        self.query_one("#overview", Overview).update_worlds(worlds)

    # -------------------------------------------------------- actions
    async def action_toggle_pause(self) -> None:
        self.paused = not self.paused
        self._refresh_hud()
        if self._ws:
            await self._ws.send({"action": "pause" if self.paused else "resume"})

    async def action_step(self) -> None:
        if self._ws:
            await self._ws.send({"action": "step"})
            self.paused = True
            self._refresh_hud()

    async def action_reset(self) -> None:
        if self._ws:
            await self._ws.send({"action": "reset"})
            self._prev_tick = None
            self.query_one("#chronicle", Chronicle).clear_events()

    def action_fit_view(self) -> None:
        self.query_one("#world", WorldView).fit()

    def action_toggle_ascii(self) -> None:
        view = self.query_one("#world", WorldView)
        view.ascii_mode = not view.ascii_mode
        view.fit()  # vertical scale differs between the two renderers

    def action_zoom_in(self) -> None:
        self.query_one("#world", WorldView).zoom_by(1 / 1.4)

    def action_zoom_out(self) -> None:
        self.query_one("#world", WorldView).zoom_by(1.4)

    def action_pan_left(self) -> None:
        self.query_one("#world", WorldView).pan(-1, 0)

    def action_pan_right(self) -> None:
        self.query_one("#world", WorldView).pan(1, 0)

    def action_pan_up(self) -> None:
        self.query_one("#world", WorldView).pan(0, -1)

    def action_pan_down(self) -> None:
        self.query_one("#world", WorldView).pan(0, 1)

    def action_inspect(self) -> None:
        if self.selected_id is not None:
            self.show_inspector(self.selected_id)

    def show_inspector(self, creature_id: int) -> None:
        self.selected_id = creature_id
        self._sync_selection()
        self.push_screen(InspectorScreen(creature_id))

    def show_clan(self, clan_id: int) -> None:
        self.push_screen(ClanDetailsScreen(clan_id))

    def action_cycle_chronicle_filter(self) -> None:
        cat = self.query_one("#chronicle", Chronicle).cycle_filter()
        self.notify(f"Chronicle filter: {cat.upper()}")

    def action_toggle_follow(self) -> None:
        view = self.query_one("#world", WorldView)
        view.follow_selected = not view.follow_selected
        self.notify(f"Camera tracking: {'ON' if view.follow_selected else 'OFF'}")

    def action_clan_of_selection(self) -> None:
        cid: int | None = None
        if self.world_state:
            for e in self.world_state.entities:
                if e.id == self.selected_id and e.kind == "creature":
                    cid = e.clan_id
                    break
        if cid is None:
            table = self.query_one("#clans-table", ClanPanel)
            cid = table.selected_clan_id
        if cid is not None:
            self.show_clan(cid)
        else:
            self.notify("select a creature or a clan row first", severity="warning")

    def action_laws(self) -> None:
        self.push_screen(GodLawsScreen())

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

    async def action_load_older(self) -> None:
        chron = self.query_one("#chronicle", Chronicle)
        try:
            data = await self.rest.history(limit=200)
        except Exception:
            self.notify("history unavailable", severity="warning")
            return
        events = list(data.get("events") or [])
        if not events:
            chron.write("<no older events>")
            return
        oldest = min(e.get("id", 0) for e in events)
        chron.add_fetched(events, self.world_state.clans if self.world_state else {})
        self.notify(f"loaded {len(events)} events from the archive (id ≤ {oldest})")

    async def action_speed(self, index: int) -> None:
        if 0 <= index < len(SPEED_PRESETS):
            self.speed = SPEED_PRESETS[index]
            self._refresh_hud()
            if self._ws:
                await self._ws.send({"action": "set_speed", "value": self.speed})
            self.notify(f"speed → {self.speed:g} ticks/s")

    # ------------------------------------------------- world click handling
    def on_world_view_creature_picked(self, event: WorldView.CreaturePicked) -> None:
        ent = event.entity
        self.selected_id = ent.id if ent is not None else None
        self._sync_selection()
