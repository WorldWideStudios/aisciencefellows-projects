"""
Plate layout model: which drug goes into which well at which concentration.

The layout is independent of the GUI so it can be saved, tested, and later
turned into an Opentrons protocol.
"""

import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

from plate_formats import PLATE_FORMATS, PlateFormat, parse_well, row_label, well_name, well_sort_key

LAYOUT_FILE_VERSION = 1

CONCENTRATION_UNITS = ["M", "mM", "µM", "nM"]
_UNIT_TO_NANOMOLAR = {"M": 1e9, "mM": 1e6, "µM": 1e3, "nM": 1.0}

ROLE_TREATMENT = "Treatment"
ROLE_VEHICLE = "Vehicle control"
ROLE_POSITIVE = "Positive control"
ROLE_UNTREATED = "Untreated"
ROLES = [ROLE_TREATMENT, ROLE_VEHICLE, ROLE_POSITIVE, ROLE_UNTREATED]

MAX_DMSO_PERCENT = 0.5


def to_nanomolar(value: float, unit: str) -> float:
    """
    Convert a molar concentration to nM.

    Parameters
    ----------
    value : float
        Concentration value.
    unit : str
        One of ``CONCENTRATION_UNITS``.

    Returns
    -------
    float
        Concentration in nM.
    """
    return value * _UNIT_TO_NANOMOLAR[unit]


def from_nanomolar(value_nm: float, unit: str) -> float:
    """Convert a concentration in nM to ``unit``."""
    return value_nm / _UNIT_TO_NANOMOLAR[unit]


@dataclass
class WellAssignment:
    """
    Contents of one well.

    Parameters
    ----------
    role : str
        One of ``ROLES``.
    drug : str
        Drug name (for vehicle controls, the solvent, e.g. ``"DMSO"``).
    concentration : float or None
        Final concentration in the well, in ``unit``.
    unit : str
        Concentration unit.
    """

    role: str = ROLE_TREATMENT
    drug: str = ""
    concentration: Optional[float] = None
    unit: str = "µM"

    def label(self) -> str:
        """Short human-readable description."""
        parts = [self.drug or "—"]
        if self.concentration is not None:
            parts.append(f"{self.concentration:g} {self.unit}")
        if self.role != ROLE_TREATMENT:
            parts.append(f"({self.role})")
        return " · ".join(parts)


@dataclass
class StockSolution:
    """
    Stock solution used to dose a drug.

    Parameters
    ----------
    concentration : float
        Stock concentration.
    unit : str
        Stock concentration unit.
    solvent : str, default="DMSO"
        Solvent of the stock.
    """

    concentration: float
    unit: str = "mM"
    solvent: str = "DMSO"


class PlateLayout:
    """
    Drug assignments for every well of one plate.

    Parameters
    ----------
    format_name : str
        Key in ``PLATE_FORMATS``.
    name : str, default="Untitled plate"
        Plate name.

    Examples
    --------
    >>> layout = PlateLayout("96-well")
    >>> layout.assign(["A1", "A2"], WellAssignment(drug="Staurosporine", concentration=1, unit="µM"))
    >>> layout.get("A1").drug
    'Staurosporine'
    """

    def __init__(self, format_name: str, name: str = "Untitled plate") -> None:
        if format_name not in PLATE_FORMATS:
            raise ValueError(f"Unknown plate format: {format_name}")
        self.format_name = format_name
        self.name = name
        self.assignments: dict[str, WellAssignment] = {}
        self.stocks: dict[str, StockSolution] = {}
        self.pipetting: dict[str, float] = {}

    @property
    def plate_format(self) -> PlateFormat:
        """The ``PlateFormat`` of this layout."""
        return PLATE_FORMATS[self.format_name]

    def all_wells(self) -> list[str]:
        """All well names in row-wise order."""
        fmt = self.plate_format
        return [well_name(row, col) for row in range(fmt.rows) for col in range(fmt.columns)]

    def _check_well(self, well: str) -> None:
        row, col = parse_well(well)
        fmt = self.plate_format
        if not (0 <= row < fmt.rows and 0 <= col < fmt.columns):
            raise ValueError(f"Well {well} is outside a {fmt.name} plate")

    def get(self, well: str) -> Optional[WellAssignment]:
        """Return the assignment of ``well``, or None if empty."""
        return self.assignments.get(well)

    def assign(self, wells: Iterable[str], assignment: WellAssignment) -> None:
        """
        Put the same contents into several wells.

        Parameters
        ----------
        wells : iterable of str
            Well names.
        assignment : WellAssignment
            Contents to copy into each well.
        """
        for well in wells:
            self._check_well(well)
            self.assignments[well] = WellAssignment(**asdict(assignment))

    def clear(self, wells: Optional[Iterable[str]] = None) -> None:
        """Empty the given wells, or the whole plate if ``wells`` is None."""
        if wells is None:
            self.assignments.clear()
            return
        for well in wells:
            self.assignments.pop(well, None)

    def apply_dose_series(
        self,
        wells: Iterable[str],
        drug: str,
        top_concentration: float,
        unit: str,
        dilution_factor: float,
        direction: str = "row",
        role: str = ROLE_TREATMENT,
    ) -> None:
        """
        Fill wells with a serial dose series, highest dose first.

        Parameters
        ----------
        wells : iterable of str
            Selected wells.
        drug : str
            Drug name.
        top_concentration : float
            Concentration of the first well in each series.
        unit : str
            Concentration unit.
        dilution_factor : float
            Fold change between neighbouring wells (> 1).
        direction : {"row", "column"}, default="row"
            ``"row"``: each row is one series running left to right
            (rows become replicates). ``"column"``: each column is one
            series running top to bottom.
        role : str, default=ROLE_TREATMENT
            Role for the wells.

        Notes
        -----
        Concentrations are rounded to 4 significant figures.
        """
        if dilution_factor <= 1:
            raise ValueError("Dilution factor must be > 1")
        if direction not in ("row", "column"):
            raise ValueError("direction must be 'row' or 'column'")

        groups: dict[int, list[tuple[int, str]]] = {}
        for well in wells:
            self._check_well(well)
            row, col = parse_well(well)
            group_key, position = (row, col) if direction == "row" else (col, row)
            groups.setdefault(group_key, []).append((position, well))

        for members in groups.values():
            for step, (_, well) in enumerate(sorted(members)):
                concentration = float(f"{top_concentration / dilution_factor ** step:.4g}")
                self.assignments[well] = WellAssignment(role, drug, concentration, unit)

    def drugs(self) -> list[str]:
        """Distinct drug names in order of first appearance (row-wise)."""
        seen: list[str] = []
        for well in sorted(self.assignments, key=well_sort_key):
            drug = self.assignments[well].drug
            if drug and drug not in seen:
                seen.append(drug)
        return seen

    def concentration_range_nm(self, drug: str) -> Optional[tuple[float, float]]:
        """Min and max concentration (nM) used for ``drug``, or None."""
        values = [
            to_nanomolar(a.concentration, a.unit)
            for a in self.assignments.values()
            if a.drug == drug and a.concentration
        ]
        return (min(values), max(values)) if values else None

    def change_format(self, format_name: str) -> list[str]:
        """
        Switch plate format, dropping wells that no longer exist.

        Returns
        -------
        list of str
            Wells that were removed.
        """
        self.format_name = format_name
        fmt = self.plate_format
        dropped = []
        for well in list(self.assignments):
            row, col = parse_well(well)
            if row >= fmt.rows or col >= fmt.columns:
                dropped.append(well)
                del self.assignments[well]
        return dropped

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        """Serialise the layout to a JSON-compatible dict."""
        return {
            "version": LAYOUT_FILE_VERSION,
            "name": self.name,
            "format": self.format_name,
            "saved": datetime.now().isoformat(timespec="seconds"),
            "wells": {
                well: asdict(a) for well, a in sorted(self.assignments.items(), key=lambda kv: well_sort_key(kv[0]))
            },
            "stocks": {drug: asdict(stock) for drug, stock in self.stocks.items()},
            "pipetting": dict(self.pipetting),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PlateLayout":
        """Rebuild a layout from ``to_dict`` output."""
        layout = cls(data["format"], data.get("name", "Untitled plate"))
        for well, values in data.get("wells", {}).items():
            layout.assign([well], WellAssignment(**values))
        for drug, values in data.get("stocks", {}).items():
            layout.stocks[drug] = StockSolution(**values)
        layout.pipetting = dict(data.get("pipetting", {}))
        return layout

    def save_json(self, path: Path) -> None:
        """
        Save the layout as JSON.

        Raises
        ------
        OSError
            If the file can't be written.
        """
        path = Path(path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError as error:
            raise OSError(f"Could not save layout to {path}: {error}") from error

    @classmethod
    def load_json(cls, path: Path) -> "PlateLayout":
        """
        Load a layout saved with ``save_json``.

        Raises
        ------
        OSError
            If the file can't be read.
        ValueError
            If the file isn't a valid layout.
        """
        path = Path(path)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except OSError as error:
            raise OSError(f"Could not read {path}: {error}") from error
        except json.JSONDecodeError as error:
            raise ValueError(f"{path.name} is not valid JSON: {error}") from error
        try:
            return cls.from_dict(data)
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"{path.name} is not a valid plate layout: {error}") from error

    def export_layout_csv(self, path: Path) -> None:
        """
        Export one row per well (including empty wells) as CSV.

        Raises
        ------
        OSError
            If the file can't be written.
        """
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["well", "row", "column", "role", "drug", "concentration", "unit"])
                for well in self.all_wells():
                    row, col = parse_well(well)
                    a = self.assignments.get(well)
                    writer.writerow([
                        well, row_label(row), col + 1,
                        a.role if a else "", a.drug if a else "",
                        "" if not a or a.concentration is None else a.concentration,
                        a.unit if a and a.concentration is not None else "",
                    ])
        except OSError as error:
            raise OSError(f"Could not export CSV to {path}: {error}") from error
