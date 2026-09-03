"""Theology mixin — faith/shrines, blessings, miracles, synods, epiphanies, dogma (BI-7)."""

from __future__ import annotations

import math
import random
from typing import Any

from ..entities import Creature, House
from ..protocol import HistoryEvent
from .constants import *

class TheologyMixin:
    def _consecrate_initial_shrines(self) -> None:
        """§AP: settled clans consecrate their shrine at founding, not on the
        first tick afterwards — keeps the first delta frame free of an
        all-clans burst (the keyframe already carries shrine_level)."""
        if not self.config.theology_enabled:
            return
        living: set[int] = set()
        for c in self.world.creatures():
            if c.clan_id:
                living.add(c.clan_id)
        for cid, info in self.clans.items():
            if cid in living and int(info.get("shrine_level", 0)) == 0:
                info["shrine_level"] = 1

    def _shrine_pos(self, cid: int) -> tuple[float, float] | None:
        """The shrine stands beside the clan's main house (east wall); faith
        follows the people, so a clanless-of-roof clan falls back to any
        claimed roof. None when the clan is homeless."""
        cached = getattr(self, "_shrine_pos_by_clan", None)
        if cached is not None:
            return cached.get(cid)
        info = self.clans.get(cid)
        if not info:
            return None
        house = self.world.entities.get(info.get("main_house_id"))
        if not isinstance(house, House) or house.is_ruin or house.clan_id != cid:
            house = None
            for h in self._functional_houses():
                if isinstance(h, House) and h.clan_id == cid and not h.is_ruin:
                    house = h
                    break
        if not isinstance(house, House):
            return None
        return (house.x + house.size / 2.0 + 1.5, house.y)

    def _shrine_aura_radius(self, cid: int) -> float:
        """A level-1 shrine blesses its immediate surroundings; a temple's
        aura extends across the whole territory."""
        if int(self.clans.get(cid, {}).get("shrine_level", 0)) >= 2:
            return max(SHRINE_AURA_RADIUS, self.config.territory_radius)
        return SHRINE_AURA_RADIUS

    def _clan_priest(self, cid: int) -> Creature | None:
        """First living priest of a clan — the voice of the avatar."""
        for m in self._clan_members.get(cid, ()):
            if m.caste == "Priest" and m.id in self.world.entities:
                return m
        for c in self.world.creatures():
            if c.clan_id == cid and c.caste == "Priest":
                return c
        return None

    def _update_faith(self) -> None:
        """§AP Theology tick — tithes at dawn & dusk fill the clan faith pool,
        the shrine aura mends the faithful, overflowing faith works seasonal
        miracles and raises temples, crisis ages convene synods, and once in
        an age an elder priest beholds the Sphere. Deterministic: hash-gates
        instead of rng draws so the world's rng stream never moves."""
        cfg = self.config
        if not cfg.theology_enabled or not self.clans:
            return
        dl = max(1, cfg.day_length)
        tod = self._time_of_day()
        at_dawn = abs(tod - 0.25) < TITHE_WINDOW
        at_dusk = abs(tod - 0.75) < TITHE_WINDOW
        season_now = self._season()

        for cid in sorted(self.clans.keys()):
            clan = self.clans[cid]
            members = [
                m for m in self._clan_members.get(cid, ())
                if m.id in self.world.entities and not m.is_predator and not m.is_herbivore
            ]
            if not members:
                continue
            shrine = self._shrine_pos(cid)
            level = int(clan.get("shrine_level", 0))
            faith = float(clan.get("faith", 0.0))
            avatar = clan.get("totem")

            # A settled clan consecrates its shrine beside the main house.
            if shrine is not None and level == 0:
                clan["shrine_level"] = 1
                level = 1
                self._log_clan_history(
                    cid, "shrine",
                    f"Consecrated a shrine to the {avatar} beside the main house (Day {self.day})",
                )

            if shrine is not None and level >= 1:
                aura2 = self._shrine_aura_radius(cid) ** 2

                # Morning & evening tithes: the devout offer energy at the totem base.
                if (at_dawn or at_dusk) and cfg.tithe_rate > 0:
                    gained = 0.0
                    for m in members:
                        if m.energy < cfg.energy_max * 0.6:
                            continue
                        if self.world.distance_sq(m.x, m.y, *shrine) > aura2:
                            continue
                        tithe = cfg.energy_max * cfg.tithe_rate * (2.0 if m.caste == "Priest" else 1.0)
                        m.energy -= tithe
                        gained += tithe
                    faith += gained

                # The blessing aura mends the faithful while the pool holds out.
                for m in members:
                    if faith <= BLESS_FAITH_COST:
                        break
                    if m.health >= m.max_health:
                        continue
                    if self.world.distance_sq(m.x, m.y, *shrine) > aura2:
                        continue
                    healed = min(m.max_health, m.health + BLESS_HEAL_RATE) - m.health
                    if healed > 0:
                        m.health += healed
                        faith -= BLESS_FAITH_COST

                # Seasonal miracle: faith overflowing at the turn of a season.
                if (
                    self._last_season is not None
                    and season_now != self._last_season
                    and faith >= MIRACLE_FAITH_COST
                ):
                    faith -= MIRACLE_FAITH_COST
                    clan["faith"] = round(faith, 2)
                    self._work_miracle(cid, clan, shrine)

                # Temple upgrade: high faith raises stone to the Sphere.
                if level == 1 and faith >= cfg.temple_faith_cost:
                    faith -= cfg.temple_faith_cost
                    clan["shrine_level"] = 2
                    self._emit(HistoryEvent(
                        type="temple", tick=self.tick + 1, entity_id=0,
                        x=round(shrine[0], 2), y=round(shrine[1], 2),
                        payload={"clan_id": cid, "clan_name": clan.get("name"), "avatar": avatar},
                    ))
                    self._log_clan_history(
                        cid, "temple",
                        f"Raised the {avatar} shrine into a glowing Temple of the Sphere (Day {self.day})",
                    )

            clan["faith"] = round(faith, 2)

        self._last_season = season_now

        # The Great Synod of the Sphere — crisis ages unify the clans (§AP Phase D).
        age = self._age()
        if age in ("Ice", "Plague") and self.tick % SYNOD_INTERVAL == (self.config.seed % SYNOD_INTERVAL):
            self._hold_synod(age)

        # The 3D Epiphany — rare enlightenment at a temple (§AP Phase E).
        self._maybe_epiphany()

    def _work_miracle(self, cid: int, clan: dict, shrine: tuple[float, float]) -> None:
        """A seasonal miracle — the avatar gifts a mature bounty around the
        shrine and mends its whole flock."""
        cfg = self.config
        for i in range(MIRACLE_FOOD):
            ang = ((self.tick * 31 + i * 97 + self.config.seed + cid * 7) % 6283) / 1000.0
            rad = 1.5 + (i % 3) * 1.3
            x, y = self.world.normalize(
                shrine[0] + math.cos(ang) * rad,
                shrine[1] + math.sin(ang) * rad,
            )
            self.world.add(self._new_food(x, y, growth=1.0))
        for m in self._clan_members.get(cid, ()):
            if m.id not in self.world.entities or m.is_predator or m.is_herbivore:
                continue
            m.health = min(m.max_health, m.health + 20.0)
            m.energy = min(cfg.energy_max, m.energy + 10.0)
            m.emote = "cheer"
            m.emote_ticks = 30
        self._emit(HistoryEvent(
            type="miracle", tick=self.tick + 1, entity_id=0,
            x=round(shrine[0], 2), y=round(shrine[1], 2),
            payload={"clan_id": cid, "clan_name": clan.get("name"), "avatar": clan.get("totem")},
        ))
        self._log_clan_history(
            cid, "miracle",
            f"The {clan.get('totem')} granted a miracle: food bloomed around the shrine (Day {self.day})",
        )

    def _hold_synod(self, age: str) -> None:
        """§AP Phase D: during global crises the priests convene at a neutral
        centre; every clan warms toward every other and strife is stilled."""
        priest_clans = {
            c.clan_id for c in self._get_creatures()
            if c.caste == "Priest" and c.clan_id and c.id in self.world.entities
        }
        if len(priest_clans) < 2:
            return
        shrines = [p for p in (self._shrine_pos(c) for c in sorted(priest_clans)) if p]
        cx = sum(p[0] for p in shrines) / len(shrines)
        cy = sum(p[1] for p in shrines) / len(shrines)
        for pair in list(self.relations.keys()):
            self.relations[pair] = min(100, self.relations[pair] + SYNOD_RELATION_BOOST)
        self.truce_ticks = TRUCE_TICKS
        self._emit(HistoryEvent(
            type="synod", tick=self.tick + 1, entity_id=0,
            x=round(cx, 2), y=round(cy, 2),
            payload={"age": age, "clans": sorted(priest_clans),
                     "clan_names": [self.clans[c].get("name") for c in sorted(priest_clans)]},
        ))

    def _maybe_epiphany(self) -> None:
        """§AP Phase E: once in a great age, an elder priest of a temple clan
        perceives the true 3D nature of the Sphere — sectarian strife stills."""
        day_index = self.tick // max(1, self.config.day_length)
        key = (day_index, self.config.seed % EPIPHANY_PERIODS_GAP)
        if getattr(self, "_epiphany_day_seen", None) == key:
            return
        for cid in sorted(self.clans.keys()):
            clan = self.clans[cid]
            if int(clan.get("shrine_level", 0)) < 2:
                continue
            if (self.config.seed * 31 + cid * 17 + day_index) % EPIPHANY_PERIODS_GAP != 0:
                continue
            priest = self._clan_priest(cid)
            if priest is None or priest.stage != "elder":
                continue
            self._epiphany_day_seen = key
            for pair in list(self.relations.keys()):
                self.relations[pair] = min(100, self.relations[pair] + 10)
            self.truce_ticks = TRUCE_TICKS * 2
            priest.emote = "heal"
            priest.emote_ticks = 60
            priest.skills["healing"] = priest.skills.get("healing", 0.0) + 5.0
            self._emit(HistoryEvent(
                type="epiphany", tick=self.tick + 1, entity_id=priest.id,
                caste=priest.caste, x=round(priest.x, 2), y=round(priest.y, 2),
                payload={
                    "clan_id": cid, "clan_name": clan.get("name"),
                    "avatar": clan.get("totem"),
                    "personal_name": personal_name_for(priest.id, self.config.seed, priest.generation),
                    "glyph": glyph_for(priest.id, self.config.seed, priest.generation),
                },
            ))
            self._log_clan_history(
                cid, "epiphany",
                f"An elder priest beheld the Sphere in three dimensions — strife stilled (Day {self.day})",
            )
            return

    def on_law_change(self, names: list[str]) -> None:
        """§AP Phase C: Divine Law Resonance — when God adjusts any law, every
        Totem Shrine emits harmonic chimes and radiant pulses, and priests
        deliver doctrinal sermons interpreting the change per their avatar's
        dogma (morale rally within the aura). Called from the god-law endpoint;
        never touches the rng."""
        # §AQ PH-10: the law-change physical wave — a shimmer front sweeps
        # the map while the new law settles (cosmology precedes doctrine).
        self.law_wave = {"born_tick": self.tick}
        # Phase 6.3: Re-bake physical trait caches when baseline physical laws change
        try:
            bake_keys = {"morphology_annealing_enabled", "annealing_start_generation", "annealing_decay_generations", "morph_lambda_override", "vertex_mutation_std", "angle_mutation_std", "topological_mutation_rate", "energy_max", "energy_decay_per_tick", "steer_turn", "euthanasia_threshold", "attack_damage", "safeguard_enabled", "safeguard_critical_pop", "safeguard_relief_ratio", "safeguard_genesis_batch", "safeguard_morph_mercy"}
            if any(k in bake_keys for k in names) and getattr(self, "_soa", None) is not None and _morphology is not None:
                # batch re-bake all active
                try:
                    from ..morphology_engine import bake_physical_traits as _bake  # type: ignore
                except Exception:
                    _bake = getattr(_morphology, "bake_physical_traits", None) or getattr(_morphology, "bake_traits_for_index", None)  # type: ignore
                if _bake is not None:
                    try:
                        # new API batch
                        _bake(self._soa, None, self.config)  # type: ignore
                    except TypeError:
                        # fallback single
                        for idx in range(getattr(self._soa, "N", 0)):
                            try:
                                _morphology.bake_traits_for_index(idx, self._soa, self.config)  # type: ignore
                            except Exception:
                                pass
        except Exception:
            pass
        if not names or not self.config.theology_enabled:
            return
        chimes = 0
        sermons = 0
        for cid in sorted(self.clans.keys()):
            clan = self.clans[cid]
            if int(clan.get("shrine_level", 0)) < 1:
                continue
            shrine = self._shrine_pos(cid)
            if shrine is None:
                continue
            self.signals.append({
                "x": round(shrine[0], 2), "y": round(shrine[1], 2),
                "kind": "chime", "sender": 0,
                "clan_id": cid, "born_tick": self.tick, "ttl": 15,
            })
            chimes += 1
            priest = self._clan_priest(cid)
            if priest is None:
                continue
            dogma = AVATAR_DOGMA.get(clan.get("totem"), "the Sphere reshapes the world")
            law_txt = ", ".join(n.replace("_", " ") for n in names[:4])
            self._emit(HistoryEvent(
                type="sermon", tick=self.tick + 1, entity_id=priest.id,
                caste=priest.caste, x=round(priest.x, 2), y=round(priest.y, 2),
                payload={
                    "clan_id": cid, "clan_name": clan.get("name"),
                    "avatar": clan.get("totem"), "laws": names[:4],
                    "text": f"{priest.caste} proclaims: '{dogma}' — the law of {law_txt} fulfils it",
                },
            ))
            sermons += 1
            # Rallying morale: the flock within the aura draws strength.
            aura2 = self._shrine_aura_radius(cid) ** 2
            for m in self._clan_members.get(cid, ()):
                if m.id not in self.world.entities or m.is_predator or m.is_herbivore:
                    continue
                if self.world.distance_sq(m.x, m.y, *shrine) <= aura2:
                    m.energy = min(self.config.energy_max, m.energy + 2.0)
        if chimes or sermons:
            self._emit(HistoryEvent(
                type="resonance", tick=self.tick + 1, entity_id=0, x=0.0, y=0.0,
                payload={"laws": names, "chimes": chimes, "sermons": sermons},
            ))
        # §AS L-6: the chiefs interpret God's will — bold frames it as a call
        # to arms, the peaceful as a farming blessing. Never touches the rng.
        for cid in sorted(self.clans.keys()):
            info = self.clans[cid]
            lid = info.get("leader_id")
            leader = self.world.entities.get(lid) if lid is not None else None
            if not isinstance(leader, Creature):
                continue
            tone = "war" if leader.trait == "bold" else "blessing"
            if len(self.signals) < SIGNALS_MAX:
                self.signals.append({
                    "x": round(leader.x, 2), "y": round(leader.y, 2),
                    "kind": "interpret", "tone": tone, "sender": leader.id,
                    "clan_id": cid or None, "born_tick": self.tick, "ttl": 15,
                })

