"""STATUS_SPEC v1.2 API tests against the FastAPI app.

The Pi hardware (RPi.GPIO, smbus2) is not present in the test environment;
tests construct the app via :func:`build_app` with a hand-rolled fake actuator,
so the SashActuator class itself is never instantiated.
"""

from __future__ import annotations

import threading
from typing import Any

import pytest
from fastapi.testclient import TestClient

from hood_sash_automation.api.api_service import build_app
from hood_sash_automation.api.claims import ClaimRegistry


class FakeMovementThread:
    def __init__(self, alive: bool):
        self._alive = alive

    def is_alive(self) -> bool:
        return self._alive


class FakeActuator:
    """Minimal stand-in for :class:`SashActuator` used by the API tests."""

    def __init__(
        self,
        *,
        position: int | None = 1,
        is_moving: bool = False,
        target_position: int | None = None,
    ):
        self._position = position
        self.movement_thread: threading.Thread | None = (
            FakeMovementThread(True) if is_moving else None  # type: ignore[assignment]
        )
        self.target_position = target_position
        self.move_calls: list[int] = []
        self.stop_calls = 0
        self.next_move_succeeds = True

    def get_current_position(self) -> int | None:
        return self._position

    def move_to_position_async(self, position: int) -> bool:
        self.move_calls.append(position)
        if not self.next_move_succeeds:
            return False
        self.movement_thread = FakeMovementThread(True)  # type: ignore[assignment]
        self.target_position = position
        return True

    def stop(self) -> None:
        self.stop_calls += 1
        self.movement_thread = None
        self.target_position = None

    def clean_exit(self) -> None:
        pass


@pytest.fixture
def actuator() -> FakeActuator:
    return FakeActuator(position=1, is_moving=False)


@pytest.fixture
def client(actuator: FakeActuator) -> TestClient:
    app = build_app(
        actuator=actuator,
        equipment_id="fume_hood_actuator",
        equipment_name="Fume Hood Actuator",
        equipment_version="1.1.0",
        claims=ClaimRegistry(),
    )
    return TestClient(app)


def _claim(client: TestClient, *, owner: str = "test", session_id: str = "s1") -> str:
    r = client.post(
        "/control/claim",
        json={"owner": owner, "session_id": session_id, "ttl_s": 30.0},
    )
    assert r.status_code == 200, r.text
    return r.json()["claim_token"]


# -- Probe / health / status ----------------------------------------------------


def test_probe(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["protocol_version"] == "1.2"
    assert body["equipment_id"] == "fume_hood_actuator"


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "healthy"}


def test_status_ready_no_claim(client: TestClient) -> None:
    r = client.get("/status")
    assert r.status_code == 200
    body = r.json()
    assert body["equipment_status"] == "ready"
    assert body["allowed_actions"] == ["sash.move", "sash.stop"]
    assert body["details"]["claimed_by"] is None
    assert body["components"]["sash"]["state"] == "position_1"


def test_status_requires_init_when_between_sensors(actuator: FakeActuator, client: TestClient) -> None:
    actuator._position = None
    r = client.get("/status")
    body = r.json()
    assert body["equipment_status"] == "requires_init"
    assert body["allowed_actions"] == ["sash.move"]
    assert body["required_actions"] == ["sash.move"]


def test_status_busy_omits_stop_only(actuator: FakeActuator, client: TestClient) -> None:
    actuator.movement_thread = FakeMovementThread(True)  # type: ignore[assignment]
    actuator.target_position = 4
    body = client.get("/status").json()
    assert body["equipment_status"] == "busy"
    assert body["allowed_actions"] == ["sash.stop"]
    assert body["metrics"]["target_position"]["value"] == 4


def test_status_surfaces_claim(client: TestClient) -> None:
    _claim(client, owner="alice")
    body = client.get("/status").json()
    assert body["details"]["claimed_by"]["owner"] == "alice"


# -- Claim lifecycle ------------------------------------------------------------


def test_claim_then_release(client: TestClient) -> None:
    token = _claim(client)
    r = client.post("/control/release", headers={"X-Claim-Token": token})
    assert r.status_code == 204


def test_claim_conflict_returns_409(client: TestClient) -> None:
    _claim(client, session_id="s1", owner="alice")
    r = client.post(
        "/control/claim",
        json={"owner": "bob", "session_id": "s2", "ttl_s": 30.0},
    )
    assert r.status_code == 409
    body = r.json()
    assert body["detail"]["claimed_by"]["owner"] == "alice"


def test_claim_reclaim_same_session_rotates_token(client: TestClient) -> None:
    t1 = _claim(client, session_id="s1")
    t2 = _claim(client, session_id="s1")
    assert t1 != t2  # rotated
    # Old token is stale now
    r = client.post("/control/heartbeat", headers={"X-Claim-Token": t1})
    assert r.status_code == 401
    # New token is alive
    r = client.post("/control/heartbeat", headers={"X-Claim-Token": t2})
    assert r.status_code == 204


def test_heartbeat_unknown_token_401(client: TestClient) -> None:
    r = client.post("/control/heartbeat", headers={"X-Claim-Token": "nope"})
    assert r.status_code == 401


def test_release_unknown_token_is_idempotent(client: TestClient) -> None:
    r = client.post("/control/release", headers={"X-Claim-Token": "nope"})
    assert r.status_code == 204


# -- Sash control ---------------------------------------------------------------


def test_sash_move_requires_claim_token(client: TestClient) -> None:
    r = client.post("/control/sash/move", json={"position": 3})
    assert r.status_code == 423


def test_sash_move_with_valid_claim(actuator: FakeActuator, client: TestClient) -> None:
    token = _claim(client)
    r = client.post(
        "/control/sash/move",
        json={"position": 4},
        headers={"X-Claim-Token": token},
    )
    assert r.status_code == 202
    assert actuator.move_calls == [4]
    assert r.json()["equipment_status"] == "busy"


def test_sash_move_invalid_position_422(client: TestClient) -> None:
    token = _claim(client)
    r = client.post(
        "/control/sash/move",
        json={"position": 99},
        headers={"X-Claim-Token": token},
    )
    assert r.status_code == 422


def test_sash_move_already_moving_returns_409(actuator: FakeActuator, client: TestClient) -> None:
    token = _claim(client)
    actuator.next_move_succeeds = False
    r = client.post(
        "/control/sash/move",
        json={"position": 4},
        headers={"X-Claim-Token": token},
    )
    assert r.status_code == 409


def test_sash_stop_requires_claim_token(client: TestClient) -> None:
    r = client.post("/control/sash/stop")
    assert r.status_code == 423


def test_sash_stop_with_valid_claim(actuator: FakeActuator, client: TestClient) -> None:
    actuator.movement_thread = FakeMovementThread(True)  # type: ignore[assignment]
    token = _claim(client)
    r = client.post("/control/sash/stop", headers={"X-Claim-Token": token})
    assert r.status_code == 200
    assert actuator.stop_calls == 1


# -- allowed_actions / 412 mirror invariant (STATUS_SPEC §6.2) ------------------


@pytest.mark.parametrize(
    "position,is_moving,expected_state,expected_actions",
    [
        (1, False, "ready", ["sash.move", "sash.stop"]),
        (None, False, "requires_init", ["sash.move"]),
        (2, True, "busy", ["sash.stop"]),
    ],
)
def test_allowed_actions_mirror(
    position: int | None,
    is_moving: bool,
    expected_state: str,
    expected_actions: list[str],
) -> None:
    actuator = FakeActuator(position=position, is_moving=is_moving)
    app = build_app(
        actuator=actuator,
        equipment_id="fume_hood_actuator",
        equipment_name="Fume Hood Actuator",
    )
    body = TestClient(app).get("/status").json()
    assert body["equipment_status"] == expected_state
    assert body["allowed_actions"] == expected_actions
