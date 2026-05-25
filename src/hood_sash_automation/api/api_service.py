"""FastAPI service for the fume hood sash actuator.

Conforms to STATUS_SPEC v1.1: claim/heartbeat/release on ``/control/*``,
``allowed_actions`` populated, ``details.claimed_by`` surfaced on
``/status``. See ``ac-organic-lab/docs/STATUS_SPEC.md``.
"""

from __future__ import annotations

import logging
import os
import signal
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
import yaml
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from .claims import ClaimConflict, ClaimRegistry, ClaimRequired, ClaimStale
from .models import (
    PROTOCOL_VERSION,
    ClaimRejection,
    ClaimRequest,
    ClaimResponse,
    EquipmentStatus,
    HealthResponse,
    MoveRequest,
    ProbeResponse,
)
from .status_builder import build_status


_LOG = logging.getLogger(__name__)


def _load_config() -> dict:
    config_path = Path(
        os.environ.get(
            "HOOD_SASH_ACTUATOR_CONFIG",
            Path(__file__).resolve().parents[1] / "config" / "actuator_config.yaml",
        )
    )
    with open(config_path) as f:
        return yaml.safe_load(f)


def _build_actuator_config(config: dict) -> dict:
    return {
        "HALL_PINS": config["hall_pins"],
        "BOUNCE_MS": config["bounce_ms"],
        "RELAY_EXT": config["relay_ext_pin"],
        "RELAY_RET": config["relay_ret_pin"],
        "I2C_BUS": config["i2c_bus"],
        "INA_ADDR": config["ina_addr"],
        "R_SHUNT": config["r_shunt"],
        "I_MAX": config["i_max"],
        "CURRENT_THRESHOLD_UP": config["current_threshold_up"],
        "CURRENT_THRESHOLD_DOWN": config["current_threshold_down"],
        "MAX_MOVEMENT_TIME": config["max_movement_time"],
        "POSITION_TIMEOUT": config["position_timeout"],
        "POSITION_STATE_FILE": config["position_state_file"],
        "LOG_DIR": config["log_dir"],
        "HOME_ON_STARTUP": config.get("home_on_startup", False),
        "EQUIPMENT_NAME": config.get("equipment_name", "Fume Hood Actuator"),
    }


def create_app() -> FastAPI:
    """Build a FastAPI app wired to a real :class:`SashActuator`.

    Tests inject a mocked actuator by calling :func:`build_app` directly
    with a pre-constructed (mocked) actuator. ``HOOD_SASH_TESTING=1``
    additionally skips the physical-button thread startup.
    """

    # Hardware deps (RPi.GPIO, smbus2, INA219) live behind these imports.
    # Deferred so tests can build_app() without a Pi present.
    from ..actuator.controller import SashActuator  # noqa: PLC0415

    config = _load_config()
    actuator = SashActuator(_build_actuator_config(config))

    if os.environ.get("HOOD_SASH_TESTING") != "1":
        _start_button_handler(actuator, config)

    return build_app(
        actuator=actuator,
        equipment_id=config.get("equipment_id", "fume_hood_actuator"),
        equipment_name=config.get("equipment_display_name", "Fume Hood Actuator"),
        equipment_version=config.get("equipment_version"),
        cors_origins=config.get("cors_origins", ["*"]),
    )


def build_app(
    *,
    actuator,
    equipment_id: str,
    equipment_name: str,
    equipment_version: str | None = None,
    cors_origins: list[str] | None = None,
    claims: ClaimRegistry | None = None,
) -> FastAPI:
    """Assemble a FastAPI app around an already-constructed actuator."""

    claims = claims or ClaimRegistry()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            yield
        finally:
            try:
                actuator.clean_exit()
            except Exception:
                _LOG.exception("clean_exit failed during shutdown")

    app = FastAPI(
        title="Fume Hood Sash Actuator",
        version=equipment_version or "1.1.0",
        lifespan=lifespan,
    )
    app.state.actuator = actuator
    app.state.claims = claims
    app.state.equipment_id = equipment_id
    app.state.equipment_name = equipment_name
    app.state.equipment_version = equipment_version

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins or ["*"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    _register_routes(app)
    return app


def _require_claim(
    request: Request,
    x_claim_token: str | None = Header(default=None),
) -> None:
    try:
        request.app.state.claims.assert_holder(x_claim_token)
    except ClaimRequired as exc:
        raise HTTPException(
            status_code=423,
            detail=ClaimRejection(
                detail="claim required",
                claimed_by=exc.claimed_by,
            ).model_dump(mode="json"),
        )


def _snapshot(app: FastAPI) -> EquipmentStatus:
    return build_status(
        actuator=app.state.actuator,
        equipment_id=app.state.equipment_id,
        equipment_name=app.state.equipment_name,
        equipment_version=app.state.equipment_version,
        claims=app.state.claims,
    )


def _register_routes(app: FastAPI) -> None:
    @app.get("/", response_model=ProbeResponse)
    def probe() -> ProbeResponse:
        return ProbeResponse(
            equipment_id=app.state.equipment_id,
            equipment_name=app.state.equipment_name,
            protocol_version=PROTOCOL_VERSION,
        )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse()

    @app.get("/status", response_model=EquipmentStatus)
    def status() -> EquipmentStatus:
        return _snapshot(app)

    @app.post("/control/claim", response_model=ClaimResponse)
    def claim(req: ClaimRequest) -> ClaimResponse:
        try:
            return app.state.claims.claim(req)
        except ClaimConflict as exc:
            raise HTTPException(
                status_code=409,
                detail=ClaimRejection(
                    detail="Device claim held by another session",
                    claimed_by=exc.claimed_by,
                ).model_dump(mode="json"),
            )

    @app.post("/control/heartbeat", status_code=204)
    def heartbeat(x_claim_token: str | None = Header(default=None)) -> Response:
        try:
            app.state.claims.heartbeat(x_claim_token)
        except ClaimStale:
            raise HTTPException(status_code=401, detail="claim token unknown or expired")
        return Response(status_code=204)

    @app.post("/control/release", status_code=204)
    def release(x_claim_token: str | None = Header(default=None)) -> Response:
        app.state.claims.release(x_claim_token)
        return Response(status_code=204)

    @app.post(
        "/control/sash/move",
        response_model=EquipmentStatus,
        status_code=202,
    )
    def sash_move(
        body: MoveRequest,
        _: None = Depends(_require_claim),
    ) -> EquipmentStatus:
        if not app.state.actuator.move_to_position_async(body.position):
            raise HTTPException(
                status_code=409,
                detail="actuator is already moving",
            )
        return _snapshot(app)

    @app.post("/control/sash/stop", response_model=EquipmentStatus)
    def sash_stop(_: None = Depends(_require_claim)) -> EquipmentStatus:
        app.state.actuator.stop()
        return _snapshot(app)


def _start_button_handler(actuator, config: dict) -> None:
    button_config = config.get("buttons", {})
    if not (button_config.get("up_pin") and button_config.get("down_pin")):
        return
    from ..actuator.buttons import PhysicalButtons  # noqa: PLC0415

    PhysicalButtons(
        actuator,
        up_pin=button_config["up_pin"],
        down_pin=button_config["down_pin"],
        stop_pin=button_config.get("stop_pin"),
    ).start()


def main() -> None:
    """Console entry point. Launches uvicorn against :func:`create_app`."""

    app = create_app()

    def _cleanup(signum, frame):
        _LOG.info("caught signal %s, shutting down", signum)
        try:
            app.state.actuator.clean_exit()
        finally:
            sys.exit(0)

    signal.signal(signal.SIGINT, _cleanup)
    signal.signal(signal.SIGTERM, _cleanup)

    port = int(os.environ.get("HOOD_SASH_PORT", "5000"))
    host = os.environ.get("HOOD_SASH_HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
