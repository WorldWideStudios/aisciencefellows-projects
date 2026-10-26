"""HTTP routes for the concoction console."""

from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

import apothecary_state
import labware_offsets
import run_store
from api.routes import _robot
from concoction import COLUMNS, Ingredient, Recipe, order_summary, protocol_source, validate_order
from medium_fill import PCR_PLATE, PCR_PLATE_URI
from simulation import simulate_protocol

router = APIRouter(prefix="/apothecary")


class IngredientBody(BaseModel):
    trough: int
    volume_ul: float


class RecipeBody(BaseModel):
    column: int
    name: str = Field("", max_length=80)
    ingredients: list[IngredientBody]


class OrderBody(BaseModel):
    plate: str = Field(min_length=1, max_length=80)
    recipes: list[RecipeBody]


class TroughBody(BaseModel):
    trough: int = Field(ge=1, le=12)
    name: str = Field(min_length=1, max_length=40)
    color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    volume_ul: Optional[float] = Field(None, ge=0, le=15000)


def _recipes(body: OrderBody) -> list[Recipe]:
    return [Recipe(r.column, [Ingredient(i.trough, i.volume_ul) for i in r.ingredients], r.name) for r in body.recipes]


def _problems(state: dict, plate: str, recipes: list[Recipe]) -> list[str]:
    tips = apothecary_state.tips_view(state)
    used = {int(c) for c in apothecary_state.plate_columns(state, plate)}
    return validate_order(recipes, used, apothecary_state.trough_volumes(state), tips["small_left"], tips["large_left"])


@router.get("/state")
def get_state(request: Request, plate: str = "") -> dict:
    state = apothecary_state.load()
    robot = request.app.state.robot
    return {
        "troughs": state["troughs"],
        "tips": apothecary_state.tips_view(state),
        "columns": apothecary_state.plate_columns(state, plate) if plate else {},
        "robot": {"host": robot.host, "mock": robot.mock},
        "calibrated": labware_offsets.find(PCR_PLATE_URI, PCR_PLATE[1]) is not None,
        "plate_columns": COLUMNS,
    }


@router.put("/troughs")
def put_troughs(troughs: list[TroughBody]) -> list[dict]:
    if sorted(t.trough for t in troughs) != list(range(1, 13)):
        raise ValueError("Send all 12 troughs, numbered 1-12")
    state = apothecary_state.load()
    state["troughs"] = [t.model_dump() for t in sorted(troughs, key=lambda t: t.trough)]
    apothecary_state.save(state)
    return state["troughs"]


@router.post("/plan")
def plan(body: OrderBody) -> dict:
    """Check an order; when it's valid, also run the generated protocol through the simulator."""
    state = apothecary_state.load()
    recipes = _recipes(body)
    problems = _problems(state, body.plate, recipes)
    simulation = None
    if not problems and recipes:
        tips = state["tips"]
        result = simulate_protocol(protocol_source(recipes, tips["small_next"], tips["large_next"]))
        simulation = {"ok": result.ok, "steps": result.steps, "error": result.error}
    return {"problems": problems, "summary": order_summary(recipes), "simulation": simulation}


@router.post("/brew")
def brew(body: OrderBody, request: Request) -> dict:
    """Generate, simulate and start the order on the robot (or the mock); record what it used."""
    state = apothecary_state.load()
    recipes = _recipes(body)
    problems = _problems(state, body.plate, recipes)
    if not recipes:
        problems.append("the order is empty")
    if problems:
        raise ValueError("; ".join(problems))
    robot = request.app.state.robot
    if not robot.mock and labware_offsets.find(PCR_PLATE_URI, PCR_PLATE[1]) is None:
        raise ValueError("The PCR plate in B3 isn't calibrated: run `uv run flex calibrate` at the robot first.")
    tips = state["tips"]
    source = protocol_source(recipes, tips["small_next"], tips["large_next"])
    simulation = simulate_protocol(source)
    if not simulation.ok:
        raise ValueError(f"Simulation failed: {simulation.error}")
    store = run_store.RunStore()
    protocol_file = store.write_file(body.plate, "concoctions.py", source)
    client = _robot(request)
    run_id = client.create_run(client.upload_protocol(protocol_file), labware_offsets=labware_offsets.for_run())
    client.action(run_id, "play")
    summary = order_summary(recipes)
    apothecary_state.record_brew(state, body.plate, recipes, summary, run_id)
    return {"run_id": run_id, "summary": summary, "steps": simulation.steps}


@router.post("/tips-refilled")
def tips_refilled() -> dict:
    state = apothecary_state.load()
    state["tips"] = {"small_next": 1, "large_next": 1}
    apothecary_state.save(state)
    return {"tips": apothecary_state.tips_view(state)}


@router.post("/plates/{plate}/clear")
def clear_plate(plate: str) -> dict:
    """Start a fresh plate under this name: forget its brewed columns."""
    state = apothecary_state.load()
    state["plates"].pop(run_store.slugify(plate), None)
    apothecary_state.save(state)
    return {"columns": {}}
