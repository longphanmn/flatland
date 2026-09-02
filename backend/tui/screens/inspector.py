"""CreatureInspector — live dossier modal for one creature (mirrors web Inspector)."""

from __future__ import annotations

import asyncio
import math
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
            yield Button("View Clan", variant="default", id="btn-insp-clan")
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
        title = ent.get("title")
        line = Text()
        line.append(f"{name} ", style=f"bold {color}")
        if title:
            line.append(f"{title} ", style="bold #ffd166")
        line.append(f"{glyph} ", style=color)
        line.append(f"#{self.creature_id}", style="dim")
        caste = ent.get("caste")
        if caste:
            line.append(f" · {caste}", style=theme.caste_color(caste))
        arch = ent.get("archetype")
        if arch:
            arch_icon = {"Apex Hunter": "⚔", "Nocturnal Forager": "🌙", "Granary Courier": "🧺", "Sentry Guard": "🛡️"}.get(arch, "◆")
            arch_color = {"Apex Hunter": "#ff7b72", "Nocturnal Forager": "#79c0ff", "Granary Courier": "#3fb950", "Sentry Guard": "#d2a8ff"}.get(arch, "#8b949e")
            line.append(f" · {arch_icon} {arch}", style=f"bold {arch_color}")
        sex = ent.get("sex")
        if sex:
            line.append(f" · {'female' if sex == 'female' else 'male'}")
        if clan:
            line.append(f" · clan {clan}", style="dim")
        gen = ent.get("generation")
        if gen is not None:
            line.append(f" · gen {gen}", style="dim")
        # BG: morph K and iso_angle
        mk = ent.get("morph_k") or ent.get("sides")
        if mk and mk != ent.get("sides"):
            line.append(f" · K{mk}", style="dim")
        iso = ent.get("iso_angle")
        if iso is not None and ent.get("sides") == 3:
            line.append(f" · θiso {iso:.1f}°", style="dim")
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
        if ent.get("torpid"):
            chips.append(("torpid", "#a5d8ff"))
        emote = ent.get("emote")
        if emote:
            chips.append((theme.EMOTE_ICONS.get(emote, emote), "#ffd166"))
        arch = ent.get("archetype")
        if arch:
            arch_col = {"Apex Hunter": "#ff7b72", "Nocturnal Forager": "#79c0ff", "Granary Courier": "#3fb950", "Sentry Guard": "#d2a8ff"}.get(arch, "#d2a8ff")
            chips.append((arch, arch_col))
        for word, col in chips:
            stxt.append(f"{word} ", style=col)
        bits = []
        pers = ent.get("personality")
        if pers:
            bits.append(theme.PERSONALITY_ICONS.get(pers, pers))
        tool = ent.get("equipped_item")
        if tool:
            bits.append(theme.ITEM_ICONS.get(tool, tool))
        fb = ent.get("food_basket", 0)
        if fb:
            bits.append(f"🧺 {fb}/3 food")
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
        iso = ent.get("iso_angle")
        if iso is not None and ent.get("sides") == 3:
            bits.append(f"θiso {iso:.1f}°")
        mk = ent.get("morph_k")
        if mk:
            bits.append(f"K{mk}")
        if ent.get("is_predator"):
            bits.append("carnivore")
        if ent.get("is_herbivore"):
            bits.append("herbivore beast")
        born = ent.get("born_tick")
        if born is not None:
            bits.append(f"born tick {born}")
        chill = ent.get("chill")
        if isinstance(chill, (int, float)) and chill > 0:
            bits.append(f"chill {chill:.1f}")
        bt = ent.get("body_temp")
        if isinstance(bt, (int, float)):
            bits.append(f"body {bt:.1f}°")
        stxt.append(" · ".join(bits), style="dim")

        # BG: Biomechanical HUD (A,P,Izz,θmin,asym,Dmult)
        morph_traits = ent.get("morph_traits")
        if morph_traits and len(morph_traits) >= 6:
            try:
                area, perim, izz, theta, asym, dmult = morph_traits[:6]
                sharp_deg = theta * 180 / math.pi if isinstance(theta, (int,float)) else 0
                stxt.append("\n🧬 Morph: ", style="bold #d2a8ff")
                stxt.append(f"A{area:.2f} P{perim:.2f} Izz{izz:.3f} θ{sharp_deg:.1f}° asym{asym:.3f} D×{dmult:.2f}", style="dim")
                # Polar radar text (mutated vs ghost)
                k = int(ent.get("morph_k") or ent.get("sides") or 4)
                stxt.append(f" · K{k}", style="dim")
                radii = ent.get("morph_radii")
                if radii and len(radii) >= k:
                    stxt.append(f" · r[{','.join(f'{v:.2f}' for v in radii[:min(k,5)])}{'...' if k>5 else ''}]", style="dim")
            except Exception:
                pass
        elif ent.get("sides"):
            stxt.append(f"\nK{ent.get('sides')} · shape {ent.get('shape') or '?'}", style="dim")

        # Skills Mastery Matrix
        skills = ent.get("skills") or {}
        if skills:
            stxt.append("\nSkills: ", style="bold #79c0ff")
            skill_bits = []
            for sk_key, sk_name in (("farming", "🌾Farm"), ("combat", "⚔️War"), ("foraging", "🦴Forage"), ("healing", "🌿Heal")):
                xp = float(skills.get(sk_key, 0.0))
                rank = "Master" if xp >= 30 else ("Adept" if xp >= 10 else "Nov")
                skill_bits.append(f"{sk_name}: {rank} ({xp:.1f}xp)")
            stxt.append("  ".join(skill_bits), style="#bc8cff")

        # BH-10: Neural hidden/outputs + heatmap text
        nn_hidden = ent.get("nn_hidden")
        nn_out = ent.get("nn_outputs")
        if isinstance(nn_hidden, (int,float)) or nn_out:
            stxt.append("\n🧠 Neural 16→12→7: ", style="bold #58a6ff")
            if isinstance(nn_hidden, (int,float)):
                stxt.append(f"h{nn_hidden:.2f} ", style="dim")
            if isinstance(nn_out, list) and len(nn_out) >= 7:
                labels = ["Thrust","Steer","Interact","Social","VocalA","VocalF","Recur"]
                out_bits = []
                for i, lab in enumerate(labels):
                    try:
                        out_bits.append(f"{lab}:{nn_out[i]:.2f}")
                    except Exception:
                        pass
                stxt.append(" ".join(out_bits), style="dim")
        nn_genome = ent.get("nn_genome")
        if isinstance(nn_genome, list) and len(nn_genome) >= 295:
            # W1 16x12, W2 12x7 heatmap as text blocks
            try:
                def _heat(v: float) -> str:
                    c = max(-2, min(2, v))
                    if c > 0.8:
                        return "█"
                    elif c > 0.3:
                        return "▓"
                    elif c > -0.3:
                        return "░"
                    elif c > -0.8:
                        return "▒"
                    else:
                        return "▓"
                stxt.append("\nW1 Sensory 16×12 (p0.03): ", style="bold #8b949e")
                # show first 2 hidden rows as example (16 cols each)
                for j in range(min(2, 12)):
                    row = "".join(_heat(nn_genome[i*12+j]) for i in range(16))
                    stxt.append(f"\n h{j}: {row}", style="dim")
                stxt.append(" …", style="dim")
                stxt.append("\nW2 Motor 12×7 (p0.05) Rec p0.02: ", style="bold #8b949e")
                for k in range(min(2, 7)):
                    row = "".join(_heat(nn_genome[204 + j*7 + k]) for j in range(12))
                    stxt.append(f"\n o{k}: {row}", style="dim")
                stxt.append(" …", style="dim")
            except Exception:
                pass
        elif ent.get("nn_genome_preview"):
            stxt.append(f"\nGenome preview: {', '.join(f'{v:.2f}' for v in ent['nn_genome_preview'][:8])}…", style="dim")

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
        elif event.button.id == "btn-insp-clan":
            ent = (self._data or {}).get("entity") or {}
            clan_id = ent.get("clan_id")
            if clan_id:
                self.dismiss()
                self.app.show_clan(clan_id)  # type: ignore[attr-defined]

    def action_close(self) -> None:
        self.dismiss()
