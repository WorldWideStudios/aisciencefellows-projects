"""
`plate`: check a layout, export its plan, and build the Flex protocol.

    uv run plate check [plate.json]
    uv run plate plan plate.json --csv transfers.csv
    uv run plate protocol plate.json [-o protocol.py]
    uv run plate simulate protocol.py
"""

from pathlib import Path
from typing import Annotated, Optional

import typer

import run_store
from cli.common import friendly_errors
from dilution_planner import export_transfers_csv
from planning import PlanResult, example_layout, plan_layout
from plate_layout import PlateLayout
from protocol_generator import generate_protocol, tube_map
from simulation import simulate_protocol

app = typer.Typer(help="Plate layouts, pipetting plans and Flex protocols.", no_args_is_help=True)

LayoutArg = Annotated[Path, typer.Argument(help="Layout JSON saved from the web UI", exists=True, dir_okay=False)]


def _load(path: Optional[Path]) -> PlateLayout:
    return PlateLayout.load_json(path) if path else example_layout()


def print_check(layout: PlateLayout, result: PlanResult, show_all: bool) -> None:
    """Print the simulation check of a plan, failures only unless ``show_all``."""
    plan, report, settings = result.plan, result.report, result.settings
    typer.echo(f"{layout.name} ({layout.format_name}), {result.volume_ul:g} µL per well, "
               f"min. transfer {settings.min_transfer_ul:g} µL")
    typer.echo(f"{len(plan.transfers)} transfers, {len(plan.intermediates)} intermediate wells, "
               f"{len(report.wells)} assay wells checked\n")
    failures = [w for w in report.wells if not w.ok]
    rows = report.wells if show_all else failures
    if rows:
        typer.echo(f"{'Well':<6}{'Expected':<18}{'Simulated':<18}{'Solvent %':<11}Status")
        for check in rows:
            status = "ok" if check.ok else f"FAIL: {check.problem}"
            typer.echo(f"{check.well:<6}{check.expected:<18}{check.simulated:<18}"
                       f"{check.solvent_percent:<11.3g}{status}")
        typer.echo("")
    for problem in report.problems:
        typer.echo(f"FAIL: {problem}")
    if report.passed:
        typer.echo(f"PASSED: all {len(report.wells)} wells reach their target; every transfer is "
                   f"≥ {settings.min_transfer_ul:g} µL and no well runs dry.")
    else:
        typer.echo(f"FAILED: {len(failures)} well(s), {len(report.problems)} transfer problem(s).")


@app.command()
@friendly_errors
def check(
    layout: Annotated[Optional[Path], typer.Argument(help="Layout JSON (default: example plate)")] = None,
    volume: Annotated[Optional[float], typer.Option(help="Final volume per assay well in µL")] = None,
    min_transfer: Annotated[Optional[float], typer.Option(help="Override the minimum transfer in µL")] = None,
    show_all: Annotated[bool, typer.Option("--all", help="List every well, not only failures")] = False,
) -> None:
    """Replay the pipetting plan and check every well."""
    plate = _load(layout)
    if min_transfer is not None:
        plate.pipetting["min_transfer_ul"] = min_transfer
    result = plan_layout(plate, volume)
    print_check(plate, result, show_all)
    if not result.report.passed:
        raise typer.Exit(1)


@app.command()
@friendly_errors
def plan(layout: LayoutArg,
         csv: Annotated[Optional[Path], typer.Option(help="Write the transfer list as CSV")] = None) -> None:
    """Print the ordered transfer list (or export it as CSV)."""
    result = plan_layout(_load(layout))
    if csv:
        export_transfers_csv(result.plan, csv)
        typer.echo(f"Wrote {len(result.plan.transfers)} transfers to {csv}")
        return
    for t in result.plan.transfers:
        typer.echo(f"{t.step:>4} {t.phase:<8} {t.source_labware}:{t.source_well:<14} → "
                   f"{t.dest_labware}:{t.dest_well:<5} {t.volume_ul:>8.2f} µL  {t.liquid}")


def build_protocol(layout: PlateLayout, output: Optional[Path] = None) -> Path:
    """
    Plan, check and generate the protocol; save layout, transfers and protocol.

    Raises
    ------
    ValueError
        If the plan fails its simulation check.
    """
    result = plan_layout(layout)
    if not result.report.passed:
        print_check(layout, result, show_all=False)
        raise ValueError("The pipetting plan fails its check; fix the layout before generating a protocol.")
    source = generate_protocol(layout, result.plan)
    store = run_store.RunStore()
    store.save_layout(layout)
    export_transfers_csv(result.plan, store.folder(layout.name) / "transfers.csv")
    path = store.write_file(layout.name, "protocol.py", source)
    if output:
        output.write_text(source, encoding="utf-8")
        path = output
    typer.echo(f"Protocol for {layout.name}: {path}")
    typer.echo("Load the stock rack:")
    for liquid, tube in tube_map(result.plan).items():
        typer.echo(f"  {tube}: {liquid}")
    return path


@app.command()
@friendly_errors
def protocol(layout: LayoutArg,
             output: Annotated[Optional[Path], typer.Option("-o", "--output", help="Also write here")] = None) -> None:
    """Generate the Flex protocol (saved in runs/<plate>/protocol.py)."""
    build_protocol(_load(layout), output)


@app.command()
@friendly_errors
def simulate(protocol_file: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
             verbose: Annotated[bool, typer.Option("-v", "--verbose", help="Print the run log")] = False) -> None:
    """Run a protocol through the Opentrons simulator."""
    result = simulate_protocol(protocol_file.read_text(encoding="utf-8"), protocol_file.name)
    if verbose and result.log:
        typer.echo(result.log)
    if not result.ok:
        typer.echo(f"Simulation FAILED: {result.error}")
        raise typer.Exit(1)
    typer.echo(f"Simulation OK: {result.steps} steps")
