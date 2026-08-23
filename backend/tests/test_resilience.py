"""Production hardening: a failed tick must never silently kill the world.

The tick loop used to die on any exception raised inside `step()` (e.g. the
DB event sink hitting `sqlite3.OperationalError: database is locked`). Because
uvicorn's lifespan holds the task reference, asyncio never reported the
exception — the world just froze at some tick while HTTP kept serving, and
only a backend restart "fixed" it.
"""

import asyncio
import sqlite3

from fastapi.testclient import TestClient

from app.config import Config
from app.main import Hub, RuntimeState, app, tick_loop


def quiet_cfg(**kw) -> Config:
    zeros = dict(
        num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0,
        num_priests=0, num_women=0, food_count=0, num_houses=0,
        weather_enabled=False,
    )
    zeros.update(kw)
    return Config(seed=7, **zeros)


def test_tick_loop_survives_step_failure_and_keeps_ticking(capsys):
    rt = RuntimeState(quiet_cfg())
    calls = {"n": 0}
    original_step = rt.sim.step

    def flaky_step():
        calls["n"] += 1
        if calls["n"] == 2:
            raise sqlite3.OperationalError("database is locked")
        original_step()

    rt.sim.step = flaky_step
    hub = Hub()

    async def drive() -> None:
        task = asyncio.create_task(tick_loop(rt, hub))
        # speed defaults to 10 tps → ~4 ticks in 0.45s; tick 2 fails loudly
        await asyncio.sleep(0.45)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    asyncio.run(drive())

    assert calls["n"] >= 3  # it kept ticking past the failure
    assert rt.last_tick_error is not None and "database is locked" in rt.last_tick_error
    out = capsys.readouterr().out
    assert "[tick-loop] step() FAILED" in out  # loud, greppable marker


def test_healthz_surfaces_last_error():
    from app.main import RT

    client = TestClient(app)
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert "tick" in body and "paused" in body
    RT.last_tick_error = "TestError: injected"
    try:
        body = client.get("/healthz").json()
        assert body["ok"] is False
        assert "injected" in body["last_tick_error"]
    finally:
        RT.last_tick_error = None
