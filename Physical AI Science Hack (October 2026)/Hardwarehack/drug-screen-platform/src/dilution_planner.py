"""
Plan pipetting for a plate layout, adding intermediate dilutions where a
direct transfer from stock would be below the pipette's minimum volume.

The plan is an ordered list of transfers (medium into intermediate wells,
intermediate preparation, then dosing of the assay plate) that a robot
protocol can execute step by step.
"""

import csv
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from plate_formats import well_name, well_sort_key
from plate_layout import (
    MAX_DMSO_PERCENT, ROLE_POSITIVE, ROLE_TREATMENT, ROLE_UNTREATED, ROLE_VEHICLE,
    PlateLayout, to_nanomolar,
)

INTERMEDIATE_ROWS = 8
INTERMEDIATE_COLUMNS = 12
INTERMEDIATE_LABWARE = "nest_96_wellplate_2ml_deep"
STOCK = "stock"
INTERMEDIATE = "intermediate"
ASSAY = "assay"
MEDIUM = "medium"


@dataclass
class PipettingSettings:
    """
    Liquid-handling limits used for planning.

    Parameters
    ----------
    min_transfer_ul : float, default=1.0
        Smallest volume the pipette handles within spec (Flex 50 µL
        pipette in low-volume mode: 1 µL).
    intermediate_transfer_ul : float, default=10.0
        Volume added from an intermediate dilution into each assay well.
    dead_volume_ul : float, default=20.0
        Extra volume left in every intermediate well.
    max_intermediate_volume_ul : float, default=2000.0
        Capacity of one intermediate well (96 deep-well plate).
    helper_volume_ul : float, default=100.0
        Volume of extra pre-dilution wells added when a stock is too
        concentrated to reach an intermediate in one step.
    """

    min_transfer_ul: float = 1.0
    intermediate_transfer_ul: float = 10.0
    dead_volume_ul: float = 20.0
    max_intermediate_volume_ul: float = 2000.0
    helper_volume_ul: float = 100.0

    def validate(self, well_volume_ul: float) -> list[str]:
        """Return a list of problems with these settings (empty if fine)."""
        problems = []
        if self.min_transfer_ul <= 0:
            problems.append("Minimum transfer must be > 0 µL")
        if self.intermediate_transfer_ul < self.min_transfer_ul:
            problems.append("Intermediate transfer must be ≥ the minimum transfer")
        if self.intermediate_transfer_ul >= well_volume_ul:
            problems.append("Intermediate transfer must be smaller than the well volume")
        if self.dead_volume_ul < 0:
            problems.append("Dead volume can't be negative")
        return problems

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> "PipettingSettings":
        """Build settings from a dict, ignoring unknown keys."""
        if not data:
            return cls()
        known = {k: float(v) for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**known)

    def to_dict(self) -> dict:
        """Serialise to a dict."""
        return asdict(self)


@dataclass
class IntermediateWell:
    """One well of the intermediate (dilution) plate."""

    well: str
    liquid: str
    concentration: float
    unit: str
    source_labware: str
    source_well: str
    source_concentration: float
    source_volume_ul: float = 0.0
    medium_volume_ul: float = 0.0
    total_volume_ul: float = 0.0
    warnings: list[str] = field(default_factory=list)

    def label(self) -> str:
        """Human-readable concentration."""
        if self.unit == "%":
            return f"{self.concentration * 100:.3g}% {self.liquid}"
        return f"{self.liquid} {_format_nm(self.concentration)}"


@dataclass
class AssayStep:
    """Dosing of one assay well."""

    well: str
    role: str
    liquid: str
    target: str
    source_labware: str
    source_well: str
    transfer_ul: Optional[float]
    medium_ul: Optional[float]
    solvent_percent: Optional[float]
    warnings: list[str] = field(default_factory=list)

    def source_label(self) -> str:
        """Short description of where the liquid comes from."""
        if self.source_labware == STOCK:
            return f"{self.source_well} stock"
        if self.source_labware == INTERMEDIATE:
            return f"Int. {self.source_well}"
        return "—"


@dataclass
class Transfer:
    """One robot transfer, in execution order."""

    step: int
    phase: str
    source_labware: str
    source_well: str
    dest_labware: str
    dest_well: str
    volume_ul: float
    liquid: str


@dataclass
class DilutionPlan:
    """Result of ``plan_dilutions``."""

    assay_steps: list[AssayStep]
    intermediates: list[IntermediateWell]
    transfers: list[Transfer]
    stock_usage_ul: dict[str, float]
    warnings: list[str]

    @property
    def needs_intermediate_plate(self) -> bool:
        """True if any intermediate dilution is required."""
        return bool(self.intermediates)


def _format_nm(value_nm: float) -> str:
    for unit, factor in (("M", 1e9), ("mM", 1e6), ("µM", 1e3)):
        if value_nm >= factor:
            return f"{value_nm / factor:.4g} {unit}"
    return f"{value_nm:.4g} nM"


@dataclass
class _Liquid:
    """A liquid to dose: a drug (concentrations in nM) or a vehicle (fractions)."""

    key: str
    stock_concentration: float
    unit: str
    stock_name: str
    targets: dict[float, list[str]] = field(default_factory=dict)


def _plan_liquid(
    liquid: _Liquid, well_volume_ul: float, settings: PipettingSettings,
) -> tuple[dict[float, tuple[float, float]], list[IntermediateWell]]:
    """
    Decide for one liquid which targets are dosed from stock and which need
    intermediates, and size the intermediate wells.

    Returns
    -------
    tuple
        ``(source_by_target, intermediates)``. ``source_by_target`` maps each
        target concentration to ``(source_concentration, transfer_ul)``; the
        source concentration equals the stock concentration for direct transfers.

    Notes
    -----
    Every dilution step is at least 2-fold, so the medium added to an
    intermediate is never a tiny, unpipettable volume.
    """
    stock = liquid.stock_concentration
    minimum = settings.min_transfer_ul
    transfer_volume = settings.intermediate_transfer_ul
    source_by_target: dict[float, tuple[float, float]] = {}
    demand: dict[float, float] = {}  # intermediate concentration -> volume drawn by assay wells

    for target, wells in liquid.targets.items():
        direct_volume = target * well_volume_ul / stock
        if direct_volume >= minimum:
            source_by_target[target] = (stock, direct_volume)
            continue
        intermediate = target * well_volume_ul / transfer_volume
        volume = transfer_volume
        if intermediate > stock / 2:
            # Barely below the minimum: a 1:2 pre-dilution with a doubled transfer is enough.
            intermediate, volume = stock / 2, 2 * direct_volume
        source_by_target[target] = (intermediate, volume)
        demand[intermediate] = demand.get(intermediate, 0.0) + volume * len(wells)

    # Choose a source for every intermediate, highest concentration first.
    # A lower-bound volume keeps the minimum-transfer check conservative.
    def bound(concentration: float) -> float:
        return max(demand[concentration] + settings.dead_volume_ul, 2 * minimum)

    source_of: dict[float, float] = {}
    lower_bound = {c: bound(c) for c in demand}
    pending = sorted(demand, reverse=True)
    while pending:
        concentration = pending.pop(0)
        sources = sorted(s for s in [stock] + list(source_of) if s >= 2 * concentration * (1 - 1e-9))
        candidates = [s for s in sources if concentration * lower_bound[concentration] / s >= minimum]
        if candidates:
            source_of[concentration] = candidates[0]
            continue
        lowest_source = sources[0]
        helper_volume = max(settings.helper_volume_ul, transfer_volume + settings.dead_volume_ul, 4 * minimum)
        # If a somewhat larger well makes the transfer pipettable, that beats an extra step.
        required_volume = minimum * lowest_source / concentration
        if required_volume <= helper_volume:
            lower_bound[concentration] = max(lower_bound[concentration], required_volume)
            source_of[concentration] = lowest_source
            continue
        # Otherwise add a helper dilution in between, diluting as far as possible
        # in one step, but never closer than 2-fold to the target.
        helper = lowest_source * minimum / helper_volume
        if helper < 2 * concentration:
            helper = 2 * concentration
            helper_volume = max(minimum * lowest_source / helper, transfer_volume + settings.dead_volume_ul,
                                2 * minimum)
        demand.setdefault(helper, 0.0)
        lower_bound[helper] = helper_volume
        pending = sorted(set(pending) | {helper, concentration}, reverse=True)

    # Size wells bottom-up: each well holds what its consumers draw plus dead volume,
    # and never less than the volume the source choice was based on.
    total: dict[float, float] = {}
    drawn_from: dict[float, float] = {c: 0.0 for c in source_of}
    for concentration in sorted(source_of):
        needed = demand[concentration] + drawn_from[concentration] + settings.dead_volume_ul
        total[concentration] = max(needed, lower_bound[concentration])
        source = source_of[concentration]
        if source in drawn_from:
            drawn_from[source] += concentration * total[concentration] / source

    intermediates = []
    for concentration in sorted(source_of, reverse=True):
        source = source_of[concentration]
        source_volume = concentration * total[concentration] / source
        item = IntermediateWell(
            well="", liquid=liquid.key, concentration=concentration, unit=liquid.unit,
            source_labware=STOCK if source == stock else INTERMEDIATE, source_well="",
            source_concentration=source, source_volume_ul=source_volume,
            medium_volume_ul=total[concentration] - source_volume, total_volume_ul=total[concentration],
        )
        if total[concentration] > settings.max_intermediate_volume_ul:
            item.warnings.append(
                f"Needs {total[concentration]:.0f} µL — more than one well holds")
        intermediates.append(item)
    return source_by_target, intermediates


def plan_dilutions(
    layout: PlateLayout, well_volume_ul: float, settings: Optional[PipettingSettings] = None,
) -> DilutionPlan:
    """
    Build the full pipetting plan for a layout.

    Parameters
    ----------
    layout : PlateLayout
        Layout with assignments and stocks.
    well_volume_ul : float
        Final volume per assay well in µL.
    settings : PipettingSettings, optional
        Liquid-handling limits. Defaults to ``PipettingSettings()``.

    Returns
    -------
    DilutionPlan

    Notes
    -----
    - Assay wells are assumed to be pre-filled with medium (e.g. seeded
      cells) to ``well_volume_ul - transfer``; ``medium_ul`` reports that.
    - Intermediates are made in medium, so the final solvent fraction is
      ``target / stock`` regardless of the dilution route.
    - Vehicle-control wells receive the highest solvent fraction used by
      any treatment with the same solvent.

    Examples
    --------
    >>> plan = plan_dilutions(layout, 100, PipettingSettings(min_transfer_ul=1))
    >>> [t.volume_ul for t in plan.transfers][:3]
    """
    settings = settings or PipettingSettings()
    problems = settings.validate(well_volume_ul)
    if problems:
        raise ValueError("; ".join(problems))

    steps: dict[str, AssayStep] = {}
    liquids: dict[str, _Liquid] = {}
    max_solvent_fraction: dict[str, float] = {}

    for well in sorted(layout.assignments, key=well_sort_key):
        assignment = layout.assignments[well]
        target_text = (f"{assignment.concentration:g} {assignment.unit}"
                       if assignment.concentration is not None else "—")
        step = AssayStep(well, assignment.role, assignment.drug, target_text, "", "", None, None, None)
        steps[well] = step

        if assignment.role == ROLE_UNTREATED:
            step.medium_ul = well_volume_ul
            continue
        if assignment.role == ROLE_VEHICLE:
            continue
        if assignment.concentration is None:
            step.warnings.append("No concentration set")
            continue
        stock = layout.stocks.get(assignment.drug)
        if stock is None:
            step.warnings.append("No stock defined")
            continue

        stock_nm = to_nanomolar(stock.concentration, stock.unit)
        target_nm = to_nanomolar(assignment.concentration, assignment.unit)
        if target_nm > stock_nm:
            step.warnings.append("Target exceeds stock concentration")
            continue

        liquid = liquids.setdefault(assignment.drug, _Liquid(assignment.drug, stock_nm, "nM", assignment.drug))
        liquid.targets.setdefault(target_nm, []).append(well)
        fraction = target_nm / stock_nm
        step.solvent_percent = 100 * fraction
        solvent_key = stock.solvent.strip().upper()
        max_solvent_fraction[solvent_key] = max(max_solvent_fraction.get(solvent_key, 0.0), fraction)
        if solvent_key == "DMSO" and step.solvent_percent > MAX_DMSO_PERCENT:
            step.warnings.append(f"DMSO > {MAX_DMSO_PERCENT:g}%")

    overall_max = max(max_solvent_fraction.values(), default=0.0)
    for step in steps.values():
        if step.role != ROLE_VEHICLE:
            continue
        solvent = step.liquid or "DMSO"
        fraction = max_solvent_fraction.get(solvent.strip().upper(), overall_max)
        if fraction <= 0:
            step.warnings.append("No treated wells to match solvent to")
            continue
        key = f"{solvent} (vehicle)"
        liquid = liquids.setdefault(key, _Liquid(key, 1.0, "%", solvent))
        liquid.targets.setdefault(fraction, []).append(step.well)
        step.solvent_percent = 100 * fraction

    # Plan each liquid and lay intermediates out on the plate, one row block per liquid.
    intermediates: list[IntermediateWell] = []
    source_lookup: dict[tuple[str, float], tuple[str, str]] = {}
    next_index = 0
    for key, liquid in liquids.items():
        source_by_target, liquid_intermediates = _plan_liquid(liquid, well_volume_ul, settings)
        if liquid_intermediates and next_index % INTERMEDIATE_COLUMNS:
            next_index += INTERMEDIATE_COLUMNS - next_index % INTERMEDIATE_COLUMNS
        for item in liquid_intermediates:
            if next_index >= INTERMEDIATE_ROWS * INTERMEDIATE_COLUMNS:
                item.well = "—"
                item.warnings.append("Intermediate plate is full")
            else:
                item.well = well_name(next_index // INTERMEDIATE_COLUMNS, next_index % INTERMEDIATE_COLUMNS)
            next_index += 1
            source_lookup[(key, item.concentration)] = (INTERMEDIATE, item.well)
        for item in liquid_intermediates:
            if item.source_labware == STOCK:
                item.source_well = liquid.stock_name
            else:
                item.source_well = source_lookup[(key, item.source_concentration)][1]
        intermediates.extend(liquid_intermediates)

        for target, wells in liquid.targets.items():
            source, volume = source_by_target[target]
            if source == liquid.stock_concentration:
                labware, source_well = STOCK, liquid.stock_name
            else:
                labware, source_well = source_lookup[(key, source)]
            for well in wells:
                step = steps[well]
                step.source_labware, step.source_well = labware, source_well
                step.transfer_ul = volume
                step.medium_ul = well_volume_ul - volume

    # Ordered transfers: medium into intermediates, intermediate prep, then dosing.
    transfers: list[Transfer] = []

    def add(phase: str, src_lw: str, src_well: str, dst_lw: str, dst_well: str, volume: float, liquid: str):
        transfers.append(Transfer(len(transfers) + 1, phase, src_lw, src_well, dst_lw, dst_well, volume, liquid))

    for item in intermediates:
        add("prepare", MEDIUM, "reservoir", INTERMEDIATE, item.well, item.medium_volume_ul, MEDIUM)
    for item in intermediates:
        add("prepare", item.source_labware, item.source_well, INTERMEDIATE, item.well,
            item.source_volume_ul, item.liquid)
    for step in sorted(steps.values(), key=lambda s: well_sort_key(s.well)):
        if step.transfer_ul:
            add("dose", step.source_labware, step.source_well, ASSAY, step.well, step.transfer_ul, step.liquid)

    stock_usage: dict[str, float] = {}
    for transfer in transfers:
        if transfer.source_labware == STOCK:
            stock_usage[transfer.liquid] = stock_usage.get(transfer.liquid, 0.0) + transfer.volume_ul

    warnings = [w for item in intermediates for w in item.warnings]
    return DilutionPlan(
        assay_steps=sorted(steps.values(), key=lambda s: well_sort_key(s.well)),
        intermediates=intermediates,
        transfers=transfers,
        stock_usage_ul=stock_usage,
        warnings=warnings,
    )


def export_transfers_csv(plan: DilutionPlan, path: Path) -> None:
    """
    Write the ordered transfer list as CSV (one row per robot transfer).

    Parameters
    ----------
    plan : DilutionPlan
        Plan from ``plan_dilutions``.
    path : Path
        Output file.

    Raises
    ------
    OSError
        If the file can't be written.
    """
    try:
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow([
                "step", "phase", "source_labware", "source_well",
                "dest_labware", "dest_well", "volume_ul", "liquid",
            ])
            for t in plan.transfers:
                writer.writerow([
                    t.step, t.phase, t.source_labware, t.source_well,
                    t.dest_labware, t.dest_well, round(t.volume_ul, 3), t.liquid,
                ])
    except OSError as error:
        raise OSError(f"Could not export transfers to {path}: {error}") from error
