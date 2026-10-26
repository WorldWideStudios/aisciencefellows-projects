"""HTTP routes: layouts, plans, protocols, robot control and run files."""

from datetime import datetime
from pathlib import Path

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path as PathParam, Request
from fastapi.responses import FileResponse, PlainTextResponse

import run_store
from api.schemas import RUN_ID_PATTERN, LayoutBody, PlateRef, RobotConfig, SnapshotBody, check_json, formats_json, plan_json
from dilution_planner import export_transfers_csv
from flex_client import client_from_env
from planning import materials, plan_layout
from plate_layout import PlateLayout
from protocol_generator import generate_protocol, tube_map
from simulation import simulate_protocol

router = APIRouter()
RunId = Annotated[str, PathParam(pattern=RUN_ID_PATTERN)]
MEDIA_TYPES = {".jpg": "image/jpeg", ".json": "application/json", ".py": "text/x-python", ".csv": "text/csv"}


def _store() -> run_store.RunStore:
    return run_store.RunStore()


def _layout(data: dict) -> PlateLayout:
    try:
        return PlateLayout.from_dict(data)
    except (KeyError, TypeError) as error:
        raise ValueError(f"Not a valid layout: {error}") from error


def _robot(request: Request):
    config: RobotConfig = request.app.state.robot
    return client_from_env(mock=config.mock, host=config.host or None, port=config.port)


@router.get("/formats")
def formats() -> list[dict]:
    return formats_json()


@router.get("/layouts")
def list_layouts() -> list[dict]:
    store = _store()
    return [{"slug": slug, "name": store.load_layout(slug).name} for slug in store.list_plates()]


@router.get("/layouts/{plate}")
def get_layout(plate: str) -> dict:
    return _store().load_layout(plate).to_dict()


@router.put("/layouts/{plate}")
def put_layout(plate: str, data: dict) -> dict:
    layout = _layout(data)
    _store().save_layout(layout)
    return {"slug": run_store.slugify(layout.name)}


@router.get("/layouts/{plate}/run")
def run_files(plate: str) -> dict:
    """Run info and which run files exist for a plate."""
    store = _store()
    folder = store.root / run_store.slugify(plate)
    files = sorted(p.name for p in folder.iterdir()) if folder.is_dir() else []
    return {"slug": run_store.slugify(plate), "files": files, "run": store.load_run_info(plate)}


@router.post("/plan")
def plan(body: LayoutBody) -> dict:
    layout = _layout(body.layout)
    result = plan_layout(layout, body.volume_ul)
    return {
        "plan": plan_json(result.plan),
        "check": check_json(result.report),
        "materials": materials(layout, result.plan),
        "volume_ul": result.volume_ul,
    }


@router.post("/plan/transfers.csv")
def transfers_csv(body: LayoutBody) -> PlainTextResponse:
    layout = _layout(body.layout)
    result = plan_layout(layout, body.volume_ul)
    path = _store().folder(layout.name) / "transfers.csv"
    export_transfers_csv(result.plan, path)
    return PlainTextResponse(path.read_text(encoding="utf-8"), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{path.parent.name}_transfers.csv"'})


@router.post("/protocol")
def protocol(body: LayoutBody) -> dict:
    """Plan, check, generate and simulate; saves layout, transfers and protocol."""
    layout = _layout(body.layout)
    result = plan_layout(layout, body.volume_ul)
    if not result.report.passed:
        raise ValueError("The pipetting plan fails its check; fix the layout before generating a protocol.")
    source = generate_protocol(layout, result.plan)
    store = _store()
    store.save_layout(layout)
    export_transfers_csv(result.plan, store.folder(layout.name) / "transfers.csv")
    store.write_file(layout.name, "protocol.py", source)
    simulation = simulate_protocol(source)
    return {
        "slug": run_store.slugify(layout.name),
        "protocol": source,
        "tubes": tube_map(result.plan),
        "simulation": {"ok": simulation.ok, "steps": simulation.steps, "error": simulation.error},
    }


@router.get("/robot/config")
def get_robot_config(request: Request) -> RobotConfig:
    return request.app.state.robot


@router.put("/robot/config")
def put_robot_config(config: RobotConfig, request: Request) -> RobotConfig:
    request.app.state.robot = config
    return config


@router.get("/robot/health")
def robot_health(request: Request) -> dict:
    return _robot(request).health()


@router.post("/robot/snapshot")
def robot_snapshot(body: SnapshotBody, request: Request) -> dict:
    path = _store().write_file(body.plate, f"{body.tag}.jpg", _robot(request).snapshot())
    stamp = int(datetime.now().timestamp())
    return {"url": f"/files/{path.parent.name}/{path.name}?v={stamp}"}


@router.post("/robot/runs")
def start_run(body: PlateRef, request: Request) -> dict:
    store = _store()
    try:
        protocol_file = store.path(body.plate, "protocol.py")
    except FileNotFoundError as error:
        raise FileNotFoundError("Generate the protocol first.") from error
    client = _robot(request)
    protocol_id = client.upload_protocol(protocol_file)
    run_id = client.create_run(protocol_id)
    client.action(run_id, "play")
    store.save_run_info(body.plate, {
        "run_id": run_id, "protocol_id": protocol_id, "robot": f"{client.host}:{client.port}",
        "started": datetime.now().isoformat(timespec="seconds"), "status": "running",
    })
    return {"run_id": run_id}


@router.get("/robot/runs/{run_id}")
def run_status(run_id: RunId, request: Request, plate: str = "") -> dict:
    data = _robot(request).run_status(run_id)
    status = {"id": run_id, "status": data.get("status"),
              "errors": [e.get("detail", str(e)) for e in data.get("errors", [])]}
    if plate and status["status"] in ("succeeded", "failed", "stopped"):
        store = _store()
        info = store.load_run_info(plate)
        if info.get("run_id") == run_id and info.get("status") != status["status"]:
            info.update(status=status["status"], errors=status["errors"],
                        finished=datetime.now().isoformat(timespec="seconds"))
            store.save_run_info(plate, info)
    return status


@router.post("/robot/runs/{run_id}/{action}")
def run_action(run_id: RunId, action: str, request: Request) -> dict:
    if action not in ("play", "pause", "stop"):
        raise HTTPException(404, f"Unknown action {action}")
    _robot(request).action(run_id, action)
    return {"id": run_id, "action": action}


@router.get("/files/{plate}/{filename}")
def run_file(plate: str, filename: str) -> FileResponse:
    path = _store().path(plate, filename)
    return FileResponse(path, media_type=MEDIA_TYPES.get(Path(filename).suffix, "application/octet-stream"),
                        headers={"Cache-Control": "no-store"})
