"""Request bodies and JSON conversion for the web API (keeps src/ free of web code)."""

from dataclasses import asdict
from typing import Literal, Optional

from pydantic import BaseModel, Field

from dilution_planner import STOCK, DilutionPlan
from plan_checker import CheckReport
from plate_formats import PLATE_FORMATS, flex_compatibility_note


class LayoutBody(BaseModel):
    """A layout as saved by ``PlateLayout.to_dict`` plus an optional well volume."""

    layout: dict
    volume_ul: Optional[float] = None


class PlateRef(BaseModel):
    plate: str


class SnapshotBody(BaseModel):
    plate: str
    tag: Literal["before", "after"]


RUN_ID_PATTERN = r"^[A-Za-z0-9-]{1,64}$"


class RobotConfig(BaseModel):
    """Robot address; ``host`` is a bare IP or host name so it can't redirect requests elsewhere."""

    host: str = Field("", pattern=r"^[A-Za-z0-9.-]{0,253}$")
    port: int = Field(31950, ge=1, le=65535)
    mock: bool = False


def formats_json() -> list[dict]:
    """Every plate format with its Flex compatibility note."""
    return [
        {**asdict(fmt), "well_count": fmt.well_count, "flex_note": flex_compatibility_note(fmt)}
        for fmt in PLATE_FORMATS.values()
    ]


def plan_json(plan: DilutionPlan) -> dict:
    """Plan as JSON with the display labels the tables need."""
    return {
        "assay_steps": [{**asdict(s), "source": s.source_label()} for s in plan.assay_steps],
        "intermediates": [
            {**asdict(i), "label": i.label(),
             "source": f"{i.source_well} stock" if i.source_labware == STOCK else f"Int. {i.source_well}"}
            for i in plan.intermediates
        ],
        "transfers": [asdict(t) for t in plan.transfers],
        "stock_usage_ul": plan.stock_usage_ul,
        "warnings": plan.warnings,
    }


def check_json(report: CheckReport) -> dict:
    """Check report as JSON."""
    return {"passed": report.passed, "problems": report.problems, "wells": [asdict(w) for w in report.wells]}
