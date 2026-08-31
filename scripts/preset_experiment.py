#!/usr/bin/env python3
"""
Comprehensive preset experiment harness for 400x300 map.
7 presets x 3 seeds (42,123,999) x 1000 ticks (checkpoints at 500,1000).
Collects population, clan/house/granary counts, war/alliance/disease events,
performance ms/tick, and derives boom vs extinction pressure.
Run via: backend/.venv/bin/python scripts/preset_experiment.py
"""
import sys
import os
import time
import json
import traceback
from dataclasses import replace
from collections import Counter, defaultdict

# ensure backend/app on path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))

from app.config import Config
from app.main import PRESETS
from app.simulation import Simulation

PRESET_ORDER = ["balance", "sustainable", "theocracy", "warlords", "chaos", "extinction", "boom"]
SEEDS = [42, 123, 999]
CHECKPOINTS = [500, 1000]
TOTAL_TICKS = 1000  # set to 2000 for deeper run; 1000 for speed
W, H = 400, 300

# Intent ranges (alive at ~1000 ticks, unless noted)
INTENT = {
    "balance":    {"range": (200, 350), "notes": "steady 200-350, moderate war/disease, ~78 houses, schism/comm/war rare"},
    "sustainable":{"range": (300, 500), "notes": "360 food, cap 450/600, calm, agriculture/granaries/banquets/temples"},
    "theocracy":  {"range": (250, 450), "notes": "high faith/temples, tithe 0.06, cost 180, banquets+theology, mid war"},
    "warlords":   {"range": (200, 400), "notes": "high war: attack 50 dmg, trespass 1.0, predation 0.04, territorial"},
    "chaos":      {"range": (150, 350), "notes": "high war (60 dmg), disease lethal, predators 0.08, fires/disasters/earthquake/lightning"},
    "extinction": {"range": (30, 180),  "notes": "cataclysmic: 120 food, winter 0.30, disease lethal 0.50, predators 0.08, war 60 dmg"},
    "boom":       {"range": (600, 1000),"notes": "500 food, cap 800/1000, birth 0.25, cooldown 80, adult 80, fast growth, peaceful"},
}

EVENT_TYPES_OF_INTEREST = ["war","conquest","alliance","rivalry","coalition_formed","coalition_joined","betrayal","peace","defection","schism","succession","outbreak","recovery","disaster","fire","predation","cannibalism","exile","takeover","ruin","temple","miracle","synod","epiphany","banquet","raid","market","caravan"]

def run_one(preset_name, seed, total_ticks, checkpoints):
    base_cfg = Config(width=W, height=H, seed=seed, tick_rate=10)
    preset_laws = PRESETS[preset_name]
    # apply preset via dataclass replace (mirrors GodLaws)
    cfg = replace(base_cfg, **{k: v for k, v in preset_laws.items() if hasattr(base_cfg, k)})
    # sanity: ensure width/height stay 400x300 even if preset somehow overrides (it doesn't)
    cfg = replace(cfg, width=W, height=H, seed=seed)
    sim = Simulation(cfg)
    # checkpoint storage
    results_by_tick = {}
    # timing
    tick_times = []
    # initial snapshot at tick 0
    def collect(tick):
        alive = len(sim._cached_creatures) if getattr(sim, "_cached_creatures", None) else 0
        dead = getattr(sim, "deaths", 0)
        dead_by_cause = dict(getattr(sim, "_death_counts", {}))
        infected = sum(1 for c in getattr(sim, "_cached_creatures", [] ) if getattr(c, "infected", False))
        # clan stats
        clans = sim.clans
        alive_clans = 0
        pop_by_clan = getattr(sim, "_clan_members", {})
        # count clans with at least 1 living member
        for cid, members in pop_by_clan.items():
            if len(members) > 0:
                alive_clans += 1
        total_clans = len(clans)
        # houses
        houses = [e for e in sim.world.entities.values() if e.kind=="house" and not getattr(e, "is_ruin", False)]
        ruins = [e for e in sim.world.entities.values() if e.kind=="house" and getattr(e, "is_ruin", False)]
        # granary / larder / faith / temple
        granary_total = sum(float(v.get("granary", 0.0)) for v in clans.values())
        granary_cap = cfg.granary_capacity
        larder_total = sum(float(v.get("larder", 0.0)) for v in clans.values())
        faith_total = sum(float(v.get("faith", 0.0)) for v in clans.values())
        shrine_levels = Counter(int(v.get("shrine_level",0)) for v in clans.values())
        temples = shrine_levels.get(2,0)+shrine_levels.get(3,0)  # level >=2 is temple-ish (config says temple cost upgrades to 2+)
        # actually temple: shrine_level >=2 (level 1 shrine, 2+ temple)
        faith_avg = faith_total / max(1, len(clans))
        granary_avg = granary_total / max(1, len(clans))
        # relations
        relations = sim.relations
        # history event counts total and last 500
        hist = list(sim.history)
        counts = Counter(e.type for e in hist)
        counts_recent = Counter(e.type for e in hist if e.tick >= tick-500) if tick>=500 else counts
        # also disease: outbreak vs recovery
        births = counts.get("birth",0)
        deaths_hist = counts.get("death",0)
        # war / alliance etc
        clan_deaths = dict(getattr(sim, "_clan_deaths", {}))
        # farm plots
        farm_plots_total = sum(len(v) for v in getattr(sim, "farm_plots", {}).values())
        # performance
        avg_ms = (sum(tick_times[-500:])/len(tick_times[-500:])*1000) if tick_times else 0
        return {
            "tick": tick,
            "alive": alive,
            "dead": dead,
            "dead_by_cause": dead_by_cause,
            "infected": infected,
            "clans_total": total_clans,
            "clans_alive": alive_clans,
            "houses": len(houses),
            "ruins": len(ruins),
            "granary_total": round(granary_total,1),
            "granary_avg": round(granary_avg,1),
            "granary_capacity_per_clan": granary_cap,
            "larder_total": round(larder_total,1),
            "faith_total": round(faith_total,1),
            "faith_avg": round(faith_avg,1),
            "shrine_levels": dict(shrine_levels),
            "temples_ge2": temples,
            "farm_plots": farm_plots_total,
            "relations_count": len(relations),
            "history_counts": dict(counts),
            "history_recent": dict(counts_recent),
            "clan_deaths_total": sum(clan_deaths.values()),
            "ms_tick_avg_last500": round(avg_ms,3),
        }

    # tick 0 snapshot
    sim._refresh_cache()  # ensure caches populated before first collect (Simulation.__init__ already does)
    results_by_tick[0] = collect(0)

    checkpoints_set = set(checkpoints)
    # also track growth curve: alive every 100 ticks
    growth_curve = {0: results_by_tick[0]["alive"]}

    for t in range(1, total_ticks+1):
        t0 = time.perf_counter()
        sim.step()
        dt = time.perf_counter() - t0
        tick_times.append(dt)
        if t in checkpoints_set or t % 100 == 0:
            growth_curve[t] = len(sim._cached_creatures)
        if t in checkpoints_set:
            results_by_tick[t] = collect(t)
        # early extinct detection
        if t>30 and len(sim._cached_creatures)==0:
            # still collect remaining checkpoints as extinct state
            for ct in checkpoints:
                if ct>t and ct not in results_by_tick:
                    results_by_tick[ct]=collect(t)
            break

    overall_avg_ms = sum(tick_times)/len(tick_times)*1000 if tick_times else 0
    p95_ms = sorted(tick_times)[int(len(tick_times)*0.95)]*1000 if tick_times else 0
    max_ms = max(tick_times)*1000 if tick_times else 0

    return {
        "preset": preset_name,
        "seed": seed,
        "config": {"food_count": cfg.food_count, "carrying_capacity": cfg.carrying_capacity, "max_population": cfg.max_population,
                   "winter_food_mult": cfg.winter_food_mult, "birth_rate": cfg.birth_rate, "adult_age": cfg.adult_age,
                   "reproduction_cooldown": cfg.reproduction_cooldown, "mate_energy_min": cfg.mate_energy_min,
                   "disease_enabled": cfg.disease_enabled, "disease_rate": cfg.disease_rate, "disease_lethality": cfg.disease_lethality,
                   "war_enabled": cfg.war_enabled, "attack_damage": cfg.attack_damage, "predator_ratio": cfg.predator_ratio,
                   "predation_enabled": cfg.predation_enabled, "trespass_decay": cfg.trespass_decay,
                   "granary_capacity": cfg.granary_capacity, "tithe_rate": cfg.tithe_rate, "temple_faith_cost": cfg.temple_faith_cost},
        "total_ticks_run": sim.tick,
        "performance": {"avg_ms": round(overall_avg_ms,3), "p95_ms": round(p95_ms,3), "max_ms": round(max_ms,3), "total_s": round(sum(tick_times),2)},
        "growth_curve": growth_curve,
        "checkpoints": results_by_tick,
        "final_alive": len(sim._cached_creatures),
        "final_dead": getattr(sim, "deaths",0),
        "final_dead_by_cause": dict(getattr(sim, "_death_counts",{})),
    }

def analyze(all_results):
    print("\n" + "="*110)
    print("PRESET ANALYSIS vs INTENT (400x300, 1000 ticks, 3 seeds each)")
    print("="*110)
    for preset in PRESET_ORDER:
        runs = [r for r in all_results if r["preset"]==preset]
        intent_low, intent_high = INTENT[preset]["range"]
        print(f"\n### {preset.upper()}  intent {intent_low}-{intent_high}  — {INTENT[preset]['notes']}")
        # table header
        print(f"{'seed':>6} | {'tick':>4} | {'alive':>5} | {'dead':>4} | {'clans':>5} | {'houses':>6} | {'granary':>7} | {'larder':>6} | {'faith':>7} | {'war':>3} | {'alnc':>4} | {'outbrk':>6} | {'pred':>4} | {'can':>3} | {'inf':>3} | {'ms/t':>5}")
        print("-"*115)
        alive_at_1k = []
        for run in sorted(runs, key=lambda r:r["seed"]):
            for ck in sorted(run["checkpoints"].keys()):
                if ck not in (500,1000):
                    continue
                cp = run["checkpoints"][ck]
                hc = cp["history_counts"]
                print(f"{run['seed']:6} | {ck:4} | {cp['alive']:5} | {cp['dead']:4} | {cp['clans_alive']:2}/{cp['clans_total']:<2} | {cp['houses']:4}+{cp['ruins']:<1} | {cp['granary_total']:7.0f} | {cp['larder_total']:6.0f} | {cp['faith_total']:7.0f} | {hc.get('war',0):3} | {hc.get('alliance',0):4} | {hc.get('outbreak',0):6} | {hc.get('predation',0):4} | {hc.get('cannibalism',0):3} | {cp['infected']:3} | {cp['ms_tick_avg_last500']:5.1f}")
                if ck==1000:
                    alive_at_1k.append(cp["alive"])
            # growth curve one-liner
            gc = run["growth_curve"]
            print(f"      growth: ", end="")
            for tt in [0,100,200,300,400,500,600,700,800,900,1000]:
                if tt in gc:
                    print(f"{tt}:{gc[tt]:3} ", end="")
            print(f" | perf avg {run['performance']['avg_ms']}ms p95 {run['performance']['p95_ms']}ms")
            # dead by cause at 1k
            dbc = run["final_dead_by_cause"]
            if dbc:
                tot = sum(dbc.values())
                top = sorted(dbc.items(), key=lambda kv:-kv[1])[:5]
                print(f"      dead_by_cause ({tot} total): " + ", ".join(f"{k}:{v}({v/tot*100:.0f}%)" for k,v in top))

        # aggregate verdict
        if alive_at_1k:
            avg_alive = sum(alive_at_1k)/len(alive_at_1k)
            mn, mx = min(alive_at_1k), max(alive_at_1k)
            status = "ON TARGET" if intent_low <= avg_alive <= intent_high else ("OVER" if avg_alive>intent_high else "UNDER")
            print(f"  => AGG alive @1k: avg {avg_alive:.0f}  min {mn} max {mx}  vs intent {intent_low}-{intent_high}  => {status}")
            if status!="ON TARGET":
                drift = avg_alive - (intent_low+intent_high)/2
                print(f"     drift {drift:+.0f} from intent center {(intent_low+intent_high)/2:.0f}")
        # intent-specific deep dives
        if preset=="boom":
            gc_avgs = defaultdict(list)
            for r in runs:
                for t,v in r["growth_curve"].items():
                    gc_avgs[t].append(v)
            print("  BOOM trajectory (avg alive):", " ".join(f"{t}:{sum(v)/len(v):.0f}" for t,v in sorted(gc_avgs.items()) if t%100==0 or t==TOTAL_TICKS))
        if preset=="extinction":
            avg_dead = sum(r["final_dead"] for r in runs)/len(runs) if runs else 0
            avg_inf = sum(r["checkpoints"][1000]["infected"] for r in runs if 1000 in r["checkpoints"])/len(runs) if runs else 0
            print(f"  EXTINCTION avg total dead {avg_dead:.0f}  infected @1k {avg_inf:.0f}")
        if preset in ("theocracy","sustainable"):
            for r in runs:
                if 1000 in r["checkpoints"]:
                    cp=r["checkpoints"][1000]
                    print(f"  seed {r['seed']}: faith {cp['faith_total']:.0f} avg {cp['faith_avg']:.1f} shrine_levels {cp['shrine_levels']} temples≥2 {cp['temples_ge2']} granary {cp['granary_total']:.0f}")

def propose_adjustments(all_results):
    print("\n" + "="*110)
    print("PROPOSED CONCRETE LAW ADJUSTMENTS (to bring each preset into intent range)")
    print("="*110)
    print("Derived from 1000-tick averages across 3 seeds. All numbers are deltas vs current PRESETS in backend/app/main.py")
    print("Validate by re-running harness after edits.\n")
    for preset in PRESET_ORDER:
        runs=[r for r in all_results if r["preset"]==preset]
        if not runs: continue
        alive_vals=[r["checkpoints"][1000]["alive"] for r in runs if 1000 in r["checkpoints"]]
        if not alive_vals: continue
        avg=sum(alive_vals)/len(alive_vals)
        low,high=INTENT[preset]["range"]
        center=(low+high)/2
        drift=avg-center
        # also collect auxiliaries
        avg_dead=sum(sum(r["final_dead_by_cause"].values()) for r in runs)/len(runs)
        hist_avg=Counter()
        for r in runs:
            hist_avg.update(r["checkpoints"][1000]["history_counts"] if 1000 in r["checkpoints"] else {})
        # average houses
        avg_houses=sum(r["checkpoints"][1000]["houses"] for r in runs if 1000 in r["checkpoints"])/len(runs)
        print(f"\n[{preset}] avg alive {avg:.0f} vs intent {low}-{high} center {center:.0f} drift {drift:+.0f} | houses {avg_houses:.0f} | wars {hist_avg.get('war',0)/len(runs):.0f} outbreaks {hist_avg.get('outbreak',0)/len(runs):.0f}")
        if preset=="balance":
            if avg>high:
                print("  OVER -> reduce food_count 240→210, plant_growth 0.05→0.04, carrying 350→300, max_pop 500→420, winter 0.72→0.65, birth_rate 0.05→0.045")
            elif avg<low:
                print("  UNDER -> increase food_count 240→270, winter 0.72→0.78, carrying 350→380, energy_decay 0.022→0.020")
            else:
                # even on target, check composition
                print("  ON TARGET band — fine-tune: keep as-is or nudge relation_drift 1.8→2.2 to keep war rare (currently war ~rare is correct)")
        elif preset=="sustainable":
            if avg<high and avg>low:
                print("  ON TARGET or slightly low/high — if avg ~<350, raise food_count 360→380, granary 500→550, rain_growth 1.30→1.35; if >500 lower birth_rate 0.05→0.045")
            elif avg<low:
                print("  UNDER -> food_count 360→400, winter 0.78→0.82, plant_growth 0.06→0.07, carrying 450→500")
            else:
                print("  OVER -> carrying 450→400, max_pop 600→520, food_count 360→300, birth_rate 0.05→0.04")
        elif preset=="theocracy":
            faiths=[r["checkpoints"][1000]["faith_total"] for r in runs if 1000 in r["checkpoints"]]
            avg_faith=sum(faiths)/len(faiths) if faiths else 0
            temples=sum(r["checkpoints"][1000]["temples_ge2"] for r in runs if 1000 in r["checkpoints"])/len(runs) if runs else 0
            status="faith OK" if avg_faith>2000 else "faith LOW"
            print(f"  faith {avg_faith:.0f} temples≥2 {temples:.1f} ({status})")
            if avg>high:
                print("  OVER pop -> lower food 320→280, carrying 400→340, birth 0.06→0.05")
            elif avg<low:
                print("  UNDER pop -> raise food 320→360, winter 0.75→0.80, carrying 400→450")
            print("  To amplify theocracy signal vs sustainable: lower temple_faith_cost 180→150, raise tithe 0.06→0.07, ensure theology_enabled stays True, keep lifespan_mult 1.1 (priests live longer)")
        elif preset=="warlords":
            wars=hist_avg.get("war",0)/len(runs)
            if wars<5:
                print(f"  War LOW ({wars:.0f}/1k ticks) — intent is high war. Raise trespass 1.0→1.5, lower alliance 65→50, rivalry -35→-20, attack_damage 50→60, coalition_threshold 40→30, relation_drift 1.2→0.6")
            elif wars>30:
                print(f"  War VERY HIGH ({wars:.0f}) — reduce attack_damage 50→35 or raise alliance_threshold 65→75")
            if avg>high:
                print("  ALSO over pop -> cut granary 400→300, larder 350→250, food 290→250")
            elif avg<low:
                print("  ALSO under pop -> raise food 290→320, granary 400→500, winter 0.65→0.70")
        elif preset=="chaos":
            wars=hist_avg.get("war",0)/len(runs); outbreaks=hist_avg.get("outbreak",0)/len(runs); fires=hist_avg.get("fire",0)/len(runs)
            print(f"  war {wars:.0f} outbreak {outbreaks:.0f} fire {fires:.0f}  intent: high war + high disease + high disasters")
            if avg>high:
                print("  OVER resilient -> lower winter 0.50→0.40, raise disease_lethality 0.45→0.55, chill_drain 0.25→0.30, exposure 0.06→0.08, plant_growth 0.045→0.035")
            elif avg<low:
                print("  UNDER collapsed too fast -> raise food 280→320, winter 0.50→0.55, lower predator 0.08→0.05, bite 55→40, disease_rate 0.08→0.06")
            else:
                if wars<10:
                    print("  War below chaos intent -> trespass 1.5→2.0, relation_drift 0.4→0.2, attack 60→70")
                if outbreaks<3:
                    print("  Disease low for chaos -> outbreak 0.001→0.002, disease_rate 0.08→0.10")
        elif preset=="extinction":
            # extinction should be 30-180 but not 0 unless intended; ensure pressure but not instant wipe
            extinct_count=sum(1 for r in runs if r["final_alive"]==0)
            print(f"  extinct runs  {extinct_count}/{len(runs)}  avg alive {avg:.0f}")
            if avg>high:
                print("  OVER survivors too many -> CUT deeper: food 120→90, winter 0.30→0.22, energy_from_food 25→20, energy_decay 0.04→0.045, disease_lethality 0.50→0.60, chill_drain 0.30→0.35, predator 0.08→0.10, fire_rate 0.0008→0.0012")
            elif avg<20 and extinct_count>=2:
                print("  UNDER wipes out instantly -> soften: food 120→150, plant 0.025→0.030, winter 0.30→0.35, disease_outbreak 0.0008→0.0005, attack 60→45, predator 0.08→0.05, chill_drain 0.30→0.24")
            else:
                print("  Borderline — keep; ensure dead_by_cause shows starvation+disease+predation+war mix; if war too low raise trespass 2.0 stays, lower alliance 85→70")
        elif preset=="boom":
            # boom should hit 600-1000 rapidly
            gcs=[r["growth_curve"] for r in runs]
            avg_at_200=sum(gc.get(200,0) for gc in gcs)/len(gcs)
            avg_at_500=sum(gc.get(500,0) for gc in gcs)/len(gcs)
            print(f"  growth 200t {avg_at_200:.0f}  500t {avg_at_500:.0f}  1000t {avg:.0f}")
            if avg<high:
                shortfall=high-avg
                print(f"  UNDER boom by ~{shortfall:.0f} -> push harder: food 500→600, plant_growth 0.08→0.10, plant_spread 0.012→0.015, winter 0.85→0.90, birth 0.25→0.30, adult_age 80→60, cooldown 80→60, mate_energy 15→12, carrying 800→1000, max_pop 1000→1300, energy_from_food 35→38, energy_decay 0.018→0.015")
                # also check schism disabled keeps unity for boom — keep disabled
            elif avg>1000+200:
                print("  OVER explosive (>1200) -> cap: max_pop 1000→900, carrying 800→700, birth 0.25→0.18, food 500→450")
            # always note performance: boom at 800+ pop stresses N150
            avg_ms=sum(r["performance"]["avg_ms"] for r in runs)/len(runs)
            print(f"  perf avg {avg_ms:.1f} ms/tick (800+ pop is CPU heavy — consider omp_threshold, spatial grid 16, or lower perceive radius if >12ms)")

    print("\nGeneric tuning levers reminder:")
    print("  Up population:  +food_count, +plant_growth_rate, +winter_food_mult, +energy_from_food, -energy_decay, +birth_rate, -adult_age, -mate_energy_min, -birth_energy_cost, -reproduction_cooldown, +carrying_capacity/+max_population, -disease/war/predation, +granary/larder/aid_rate")
    print("  Down population:+energy_decay, -food_count, -winter_food_mult, +disease_lethality/outbreak, +predator_ratio/bite_damage, +attack_damage/trespass_decay, -birth_rate, +adult_age, +reproduction_cooldown, -carrying/max_pop")
    print("  War tuning:      trespass_decay (higher=more war), relation_drift (lower=sower feuds), alliance_threshold lower=more allies (less war), rivalry_threshold higher (less negative) = more war, attack_damage, predation enabling, coalitions/betrayal flags")
    print("  Disease tuning:  outbreak_rate, disease_rate, radius, lethality, recovery_rate, weather_sickness/chill_drain")
    print("  Faith/temples:   tithe_rate, temple_faith_cost, theology_enabled, miracles, banquets_enabled")

def main():
    all_results=[]
    total_start=time.perf_counter()
    for preset in PRESET_ORDER:
        for seed in SEEDS:
            print(f"\n>>> Running preset={preset} seed={seed} for {TOTAL_TICKS} ticks (400x300) ...", flush=True)
            try:
                res=run_one(preset, seed, TOTAL_TICKS, CHECKPOINTS)
                all_results.append(res)
                cp1000=res["checkpoints"].get(1000) or res["checkpoints"].get(max(res["checkpoints"].keys()))
                print(f"    done: alive={cp1000['alive']} dead={cp1000['dead']} clans={cp1000['clans_alive']}/{cp1000['clans_total']} houses={cp1000['houses']} war={cp1000['history_counts'].get('war',0)} outbreak={cp1000['history_counts'].get('outbreak',0)} ms/tick avg {res['performance']['avg_ms']}")
            except Exception as e:
                print(f"    FAILED preset={preset} seed={seed}: {e}", flush=True)
                traceback.print_exc()
    elapsed=time.perf_counter()-total_start
    print(f"\n=== All runs complete in {elapsed:.1f}s, {len(all_results)} results ===")
    # save JSON
    out_path=os.path.join(ROOT, "scripts", "preset_experiment_results.json")
    with open(out_path, "w") as f:
        json.dump({"meta":{"W":W,"H":H,"seeds":SEEDS,"checkpoints":CHECKPOINTS,"total_ticks":TOTAL_TICKS,"presets":PRESET_ORDER,"intent":INTENT}, "results":all_results}, f, indent=2)
    print(f"Saved JSON to {out_path}")

    # analysis prints
    analyze(all_results)
    propose_adjustments(all_results)

    # summary table for quick copy
    print("\n" + "="*110)
    print("COMPACT SUMMARY (avg across 3 seeds @ 1000 ticks)")
    print("="*110)
    print(f"{'preset':<12} {'alive avg':>9} {'min':>5} {'max':>5} {'intent':>13} {'dead avg':>9} {'war avg':>7} {'houses':>6} {'ms/t':>6} verdict")
    for preset in PRESET_ORDER:
        runs=[r for r in all_results if r["preset"]==preset]
        avgs=[r["checkpoints"][1000]["alive"] for r in runs if 1000 in r["checkpoints"]]
        avg=sum(avgs)/len(avgs) if avgs else 0
        mn=min(avgs) if avgs else 0
        mx=max(avgs) if avgs else 0
        lo,hi=INTENT[preset]["range"]
        dead=sum(r["final_dead"] for r in runs)/len(runs) if runs else 0
        wars=sum(r["checkpoints"][1000]["history_counts"].get("war",0) for r in runs if 1000 in r["checkpoints"])/len(runs) if runs else 0
        houses=sum(r["checkpoints"][1000]["houses"] for r in runs if 1000 in r["checkpoints"])/len(runs) if runs else 0
        ms=sum(r["performance"]["avg_ms"] for r in runs)/len(runs) if runs else 0
        verdict="OK" if lo<=avg<=hi else ("HIGH" if avg>hi else "LOW")
        print(f"{preset:<12} {avg:9.0f} {mn:5.0f} {mx:5.0f} {f'{lo}-{hi}':>13} {dead:9.0f} {wars:7.0f} {houses:6.0f} {ms:6.1f} {verdict}")

if __name__=="__main__":
    main()
