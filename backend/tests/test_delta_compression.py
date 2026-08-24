import json
import pytest
from app.config import Config
from app.entities import Creature, Food
from app.main import RuntimeState, advance_world
from app.protocol import DeltaStateMessage, StateMessage
from app.simulation import Simulation


def test_delta_payload_structure_and_validation():
    """Verify that delta payloads match the DeltaStateMessage schema."""
    cfg = Config(seed=42, width=100, height=100, carrying_capacity=50, food_count=20)
    sim = Simulation(cfg)

    # Initial keyframe
    full = sim.snapshot_payload()
    assert full["type"] == "state"
    assert len(full["entities"]) > 0
    StateMessage.model_validate(full)

    # Step simulation
    sim.step()

    # Generate delta
    delta = sim.snapshot_delta_payload()
    assert delta["type"] == "delta_state"
    assert "upsert_entities" in delta
    assert "remove_ids" in delta
    DeltaStateMessage.model_validate(delta)


def test_delta_bandwidth_reduction():
    """Verify that delta payloads achieve massive (>=75%) bandwidth savings over full snapshots."""
    cfg = Config(seed=123, width=200, height=150, carrying_capacity=200, food_count=80)
    sim = Simulation(cfg)

    # Keyframe size
    keyframe = sim.snapshot_payload()
    keyframe_bytes = len(json.dumps(keyframe).encode("utf-8"))

    # Step 10 ticks and measure average delta size
    delta_sizes = []
    for _ in range(10):
        sim.step()
        delta = sim.snapshot_delta_payload()
        delta_bytes = len(json.dumps(delta).encode("utf-8"))
        delta_sizes.append(delta_bytes)

    avg_delta_bytes = sum(delta_sizes) / len(delta_sizes)
    savings_pct = (1.0 - (avg_delta_bytes / keyframe_bytes)) * 100.0

    print(f"\n[Bandwidth Test] Full Keyframe: {keyframe_bytes:,} bytes | Avg Delta: {avg_delta_bytes:,.0f} bytes | Savings: {savings_pct:.1f}%")
    # Assert at least 75% savings on average
    assert savings_pct >= 75.0, f"Expected >= 75% bandwidth reduction, got {savings_pct:.1f}%"


def test_delta_reconstruction_fidelity():
    """Simulate client-side delta accumulator and verify reconstructed state matches live entities."""
    cfg = Config(seed=999, width=150, height=150, carrying_capacity=100, food_count=50)
    sim = Simulation(cfg)

    # Client receives initial keyframe
    keyframe = sim.snapshot_payload()
    client_entities = {e["id"]: dict(e) for e in keyframe["entities"]}

    # Simulate 30 steps of deltas
    for _ in range(30):
        sim.step()
        delta = sim.snapshot_delta_payload()

        # Apply removals
        for rid in delta["remove_ids"]:
            client_entities.pop(rid, None)

        # Apply upserts
        for ue in delta["upsert_entities"]:
            eid = ue["id"]
            if eid in client_entities:
                client_entities[eid].update(ue)
            else:
                client_entities[eid] = dict(ue)

    # Verify client entity count and IDs match the server world exactly
    server_entities = sim.world.entities
    assert len(client_entities) == len(server_entities)
    assert set(client_entities.keys()) == set(server_entities.keys())

    # Verify positions and states of a sample of entities
    for eid, server_ent in server_entities.items():
        client_ent = client_entities[eid]
        assert client_ent["id"] == server_ent.id
        assert abs(client_ent["x"] - server_ent.x) < 0.1
        assert abs(client_ent["y"] - server_ent.y) < 0.1


def test_advance_world_periodic_keyframes():
    """Verify that advance_world broadcasts keyframes on initial/mod 60 ticks and deltas in between."""
    cfg = Config(seed=777, tick_rate=20)
    rt = RuntimeState(cfg)

    # Advance 125 ticks
    types_emitted = []
    for _ in range(125):
        payload = advance_world(rt)
        if payload is not None:
            types_emitted.append((rt.sim.tick, payload["type"]))

    # Initial tick is a keyframe
    assert types_emitted[0] == (1, "state")

    # Subsequent ticks: keyframe on tick % 60 == 0, delta on others
    for tick, ptype in types_emitted[1:]:
        if tick % 60 == 0:
            assert ptype == "state", f"Tick {tick} should be a keyframe 'state', got {ptype}"
        else:
            assert ptype == "delta_state", f"Tick {tick} should be a 'delta_state', got {ptype}"

