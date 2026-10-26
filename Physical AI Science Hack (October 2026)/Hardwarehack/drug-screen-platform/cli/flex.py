"""
`flex`: talk to the Opentrons Flex.

    uv run flex health --host 192.168.0.42
    uv run flex snapshot --tag before --plate "Example screen"
    uv run flex run runs/example-screen/protocol.py --plate "Example screen"
    uv run flex demo plate.json          # check → protocol → simulate → before → run → after

Every command takes --host/--port (or FLEX_HOST/FLEX_PORT) and --mock.
"""

import math
from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional

import typer

import run_store
from cli.common import friendly_errors
from cli.plate import build_protocol
import json

from flex_client import FlexClient, MockFlexClient, client_from_env
import labware_offsets
from medium_fill import (
    PCR_PLATE, PCR_PLATE_URI, PCR_PLATE_VERSION, POSITIONS, TIP_COLUMNS, TIPS_50_FILTER, TIPS_50_FILTER_VERSION,
    protocol_source, well_for_position,
)
from plate_layout import PlateLayout
from simulation import simulate_protocol

app = typer.Typer(help="Drive the Opentrons Flex: health, camera, runs.", no_args_is_help=True)

Host = Annotated[Optional[str], typer.Option(help="Robot IP (default: $FLEX_HOST)")]
Port = Annotated[Optional[int], typer.Option(help="Robot port (default: $FLEX_PORT or 31950)")]
Mock = Annotated[bool, typer.Option("--mock", help="Use a pretend robot")]
PlateName = Annotated[str, typer.Option("--plate", help="Plate name (selects runs/<plate>/)")]


def _client(host: Optional[str], port: Optional[int], mock: bool) -> FlexClient | MockFlexClient:
    return client_from_env(mock=mock, host=host, port=port)


def _snapshot(client, plate: str, tag: str) -> Path:
    path = run_store.RunStore().write_file(plate, f"{tag}.jpg", client.snapshot())
    typer.echo(f"Snapshot {tag}: {path}")
    return path


def _run(client, protocol_file: Path, plate: str, wait: bool) -> dict:
    store = run_store.RunStore()
    protocol_id = client.upload_protocol(protocol_file)
    offsets = labware_offsets.for_run()
    run_id = client.create_run(protocol_id, labware_offsets=offsets)
    info = {"labware_offsets": offsets, "run_id": run_id, "protocol_id": protocol_id, "robot": f"{client.host}:{client.port}",
            "started": datetime.now().isoformat(timespec="seconds"), "status": "running"}
    store.save_run_info(plate, info)
    client.action(run_id, "play")
    typer.echo(f"Run {run_id} started")
    if not wait:
        return info
    last = {"status": None}

    def progress(data: dict) -> None:
        if data.get("status") != last["status"]:
            last["status"] = data.get("status")
            typer.echo(f"  status: {last['status']}")

    final = client.wait_until_done(run_id, on_progress=progress)
    info.update(status=final.get("status"), finished=datetime.now().isoformat(timespec="seconds"),
                errors=[e.get("detail", str(e)) for e in final.get("errors", [])])
    store.save_run_info(plate, info)
    return info


@app.command()
@friendly_errors
def health(host: Host = None, port: Port = None, mock: Mock = False) -> None:
    """Check the robot is reachable and print its name and software."""
    data = _client(host, port, mock).health()
    typer.echo(f"{data.get('name')} ({data.get('robot_model')}), software {data.get('api_version')}")


@app.command()
@friendly_errors
def snapshot(plate: PlateName,
             tag: Annotated[str, typer.Option(help="before or after")] = "before",
             host: Host = None, port: Port = None, mock: Mock = False) -> None:
    """Take a deck camera picture into runs/<plate>/<tag>.jpg."""
    _snapshot(_client(host, port, mock), plate, tag)


@app.command()
@friendly_errors
def run(protocol_file: Annotated[Path, typer.Argument(exists=True, dir_okay=False)], plate: PlateName,
        wait: Annotated[bool, typer.Option(help="Follow the run until it ends")] = True,
        host: Host = None, port: Port = None, mock: Mock = False) -> None:
    """Upload a protocol, start it and (by default) follow it to the end."""
    info = _run(_client(host, port, mock), protocol_file, plate, wait)
    if info["status"] not in ("succeeded", "running"):
        raise typer.Exit(1)


@app.command()
@friendly_errors
def status(run_id: str, host: Host = None, port: Port = None, mock: Mock = False) -> None:
    """Print a run's status."""
    data = _client(host, port, mock).run_status(run_id)
    typer.echo(f"{run_id}: {data.get('status')}")


@app.command()
@friendly_errors
def pause(run_id: str, host: Host = None, port: Port = None, mock: Mock = False) -> None:
    """Pause a run."""
    _client(host, port, mock).action(run_id, "pause")
    typer.echo(f"{run_id}: pause requested")


@app.command()
@friendly_errors
def stop(run_id: str, host: Host = None, port: Port = None, mock: Mock = False) -> None:
    """Stop a run."""
    _client(host, port, mock).action(run_id, "stop")
    typer.echo(f"{run_id}: stop requested")


@app.command()
@friendly_errors
def fill(plate: PlateName,
         volume: Annotated[float, typer.Option(help="Medium per well in µL (5-50)")] = 50.0,
         position: Annotated[Optional[int], typer.Option(help="Plate column 1-12 (default: next free)")] = None,
         tip_column: Annotated[Optional[int], typer.Option(help="Filter tip column 1-12 (default: next unused)")] = None,
         yes: Annotated[bool, typer.Option("--yes", help="Don't ask before starting the run")] = False,
         uncalibrated: Annotated[bool, typer.Option("--uncalibrated", help="Run without a Z calibration of the PCR plate")] = False,
         host: Host = None, port: Port = None, mock: Mock = False) -> None:
    """8-channel medium fill into the next free column of the PCR plate."""
    calibration = labware_offsets.find(PCR_PLATE_URI, PCR_PLATE[1])
    if calibration is None and not uncalibrated:
        raise ValueError(f"The PCR plate in {PCR_PLATE[1]} has no Z calibration (a riser makes the default "
                         f"height wrong). Run `uv run flex calibrate` first, or pass --uncalibrated.")
    if calibration:
        typer.echo(f"Using {PCR_PLATE[1]} calibration: z {calibration['vector']['z']:+.1f} mm "
                   f"(measured {calibration.get('measured') or 'earlier'})")
    store = run_store.RunStore()
    folder = store.folder(plate)
    try:
        fills = json.loads((folder / "fills.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        fills = []
    used = {f["position"] for f in fills}
    if position is None:
        position = next((p for p in range(1, POSITIONS + 1) if p not in used), None)
        if position is None:
            raise ValueError(f"The PCR plate for {plate} is full ({POSITIONS} positions used).")
    if tip_column is None:
        tip_column = len(fills) % TIP_COLUMNS + 1
    well = well_for_position(position)
    source = protocol_source(position, volume, tip_column)
    protocol_file = store.write_file(plate, "medium_fill.py", source)
    simulation = simulate_protocol(source, "medium_fill.py")
    if not simulation.ok:
        raise ValueError(f"Simulation failed: {simulation.error}")
    client = _client(host, port, mock)
    typer.echo(f"Fill {volume:g} µL into position {well}, tip column {tip_column} (simulation OK)")
    if not yes and not typer.confirm(f"Start on {client.host}:{client.port}?"):
        raise typer.Exit(1)
    info = _run(client, protocol_file, plate, wait=True)
    if info["status"] != "succeeded":
        raise typer.Exit(1)
    fills.append({"position": position, "well": well, "tip_column": tip_column, "volume_ul": volume,
                  "run_id": info["run_id"], "finished": info.get("finished")})
    store.write_file(plate, "fills.json", json.dumps(fills, indent=2))
    if tip_column == TIP_COLUMNS:
        typer.echo("That was the last column of the 50 µL filter tip rack: replace it before the next fill.")


MAX_JOG_MM = 20.0
# Maintenance runs take the robot's internal pipette name (as GET /instruments reports it),
# not the protocol API load name flex_8channel_1000.
ENGINE_PIPETTE_NAME = "p1000_multi_flex"
JOG_HELP = "d N = down N mm, u N = up, x N / y N = sideways, ok = save, q = abort"
JOG_AXES = {"d": ("z", -1.0), "u": ("z", 1.0), "x": ("x", 1.0), "y": ("y", 1.0)}


def _parse_jog(text: str):
    """``"ok"``, ``"q"``, ``(axis, signed mm)`` or None for anything else."""
    parts = text.strip().lower().split()
    if parts in (["ok"], ["q"]):
        return parts[0]
    if len(parts) != 2 or parts[0] not in JOG_AXES:
        return None
    try:
        distance = float(parts[1])
    except ValueError:
        return None
    if not math.isfinite(distance):  # nan would slip past the step limit
        return None
    axis, sign = JOG_AXES[parts[0]]
    return axis, sign * distance


@app.command()
@friendly_errors
def calibrate(
    slot: Annotated[str, typer.Option(help="Deck slot of the labware")] = PCR_PLATE[1],
    load_name: Annotated[str, typer.Option(help="Labware load name")] = PCR_PLATE[0],
    version: Annotated[int, typer.Option(help="Labware definition version")] = PCR_PLATE_VERSION,
    well: Annotated[str, typer.Option(help="Well to align the tips with")] = "A1",
    start_height: Annotated[float, typer.Option(help="Start this many mm above the default top (> riser height)")] = 80.0,
    tip_column: Annotated[int, typer.Option(help="50 µL filter tip column to borrow (returned afterwards)")] = 12,
    host: Host = None, port: Port = None,
) -> None:
    """Measure a labware's real height (e.g. on a riser) by jogging the tips down to its well tops."""
    client = _client(host, port, False)
    run_id = client.start_maintenance()
    command = lambda kind, **params: client.maintenance_command(run_id, kind, params)  # noqa: E731
    pipette = tips = None
    saved = False
    try:
        command("home")
        pipette = command("loadPipette", pipetteName=ENGINE_PIPETTE_NAME, mount="left")["pipetteId"]
        tips = command("loadLabware", location={"slotName": TIPS_50_FILTER[1]}, loadName=TIPS_50_FILTER[0],
                       namespace="opentrons", version=TIPS_50_FILTER_VERSION)["labwareId"]
        target = command("loadLabware", location={"slotName": slot}, loadName=load_name,
                         namespace="opentrons", version=version)["labwareId"]
        command("pickUpTip", pipetteId=pipette, labwareId=tips, wellName=f"A{tip_column}")
        command("moveToWell", pipetteId=pipette, labwareId=target, wellName=well,
                wellLocation={"origin": "top", "offset": {"x": 0, "y": 0, "z": start_height}})
        typer.echo(f"Tips are {start_height:g} mm above where the robot expects the top of {well} in {slot}.")
        typer.echo(f"Jog until the tip ends are level with the well tops. {JOG_HELP}")
        offset = {"x": 0.0, "y": 0.0, "z": start_height}
        while True:
            jog = _parse_jog(typer.prompt("jog"))
            if jog == "q":
                raise typer.Exit(1)
            if jog == "ok":
                break
            if jog is None:
                typer.echo(f"Unknown command. {JOG_HELP}")
                continue
            axis, distance = jog
            if abs(distance) > MAX_JOG_MM:
                typer.echo(f"Steps are at most {MAX_JOG_MM:g} mm; jog in smaller steps.")
                continue
            command("moveRelative", pipetteId=pipette, axis=axis, distance=distance)
            offset[axis] = round(offset[axis] + distance, 2)
            typer.echo(f"  offset x {offset['x']:+.2f}  y {offset['y']:+.2f}  z {offset['z']:+.2f} mm")
        definition_uri = f"opentrons/{load_name}/{version}"
        if typer.confirm(f"Save offset z {offset['z']:+.2f} mm (x {offset['x']:+.2f}, y {offset['y']:+.2f}) "
                         f"for {load_name} in {slot}?"):
            labware_offsets.save_offset(definition_uri, slot, offset, datetime.now().isoformat(timespec="seconds"))
            saved = True
            typer.echo("Saved. Every run started from this laptop now uses it.")
    finally:
        try:
            if pipette and tips:
                command("moveRelative", pipetteId=pipette, axis="z", distance=20)
                command("dropTip", pipetteId=pipette, labwareId=tips, wellName=f"A{tip_column}")
            command("home")
        finally:
            client.end_maintenance(run_id)
    if not saved:
        raise typer.Exit(1)


@app.command()
@friendly_errors
def demo(layout_file: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
         host: Host = None, port: Port = None, mock: Mock = False) -> None:
    """Check, generate, simulate, snapshot before, run, snapshot after."""
    client = _client(host, port, mock)
    layout = PlateLayout.load_json(layout_file)
    typer.echo(f"Robot: {client.health().get('name')}")
    protocol_file = build_protocol(layout)
    simulation = simulate_protocol(protocol_file.read_text(encoding="utf-8"))
    if not simulation.ok:
        typer.echo(f"Simulation FAILED: {simulation.error}")
        raise typer.Exit(1)
    typer.echo(f"Simulation OK: {simulation.steps} steps")
    _snapshot(client, layout.name, "before")
    info = _run(client, protocol_file, layout.name, wait=True)
    _snapshot(client, layout.name, "after")
    typer.echo(f"Run {info['status']}. Files in {run_store.RunStore().folder(layout.name)}")
    if info["status"] != "succeeded":
        raise typer.Exit(1)
