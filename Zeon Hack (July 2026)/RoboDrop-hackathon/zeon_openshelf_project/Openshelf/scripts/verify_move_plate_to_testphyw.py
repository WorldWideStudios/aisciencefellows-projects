#!/usr/bin/env python3
"""Verify the frozen pickup plus right-arm OpenShelf placement workflow."""

from __future__ import annotations

import ast
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import verify_zeon_project as project_gate


ROOT = Path(__file__).resolve().parents[1]
PICKUP_PATH = ROOT / "skills" / "pickup_plate" / "robotic_code.py"
PLACE_PATH = (
    ROOT / "skills" / "place_plate_at_testphyw" / "robotic_code.py"
)
WORKFLOW_PATH = (
    ROOT / "workflows" / "move_plate_to_openshelf_testphyw.json"
)
PROJECT_PATH = ROOT / "project.json"
PLATE_MODEL_PATH = (
    ROOT / "objects" / "wellplate_pcr" / "wellplate_pcr.object_model.yaml"
)
SHELF_MODEL_PATH = (
    ROOT / "objects" / "openshelf" / "openshelf.object_model.yaml"
)
WORLD_PATH = ROOT / "worlds" / "openshelf_sucess" / "world_state.json"

FROZEN_PICKUP_SHA256 = (
    "15003fe68e84e26065ac2261f0126103389d175206ef396b9499f0cec1b0aa90"
)
EXPECTED_WORKFLOW = "move_plate_to_openshelf_testphyw"
EXPECTED_WORLD = "openshelf_sucess"
EXPECTED_SECOND_TRANSITION = [
    0.250,
    0.112,
    -0.858,
    -1.347,
    1.777,
    2.382,
]


class Contract:
    def __init__(self) -> None:
        self.checks = 0
        self.errors: list[str] = []

    def check(self, condition: bool, message: str) -> None:
        if condition:
            self.checks += 1
            print(f"PASS  {message}")
        else:
            self.errors.append(message)
            print(f"ERROR {message}")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_yaml(path: Path) -> Any:
    reporter = project_gate.Reporter()
    value = project_gate.load_yaml(path, reporter)
    if reporter.errors or value is None:
        raise ValueError("; ".join(reporter.errors) or f"cannot parse {path}")
    return value


def assignments(tree: ast.Module) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            try:
                values[node.targets[0].id] = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                continue
    return values


def keyword_value(call: ast.Call, name: str) -> ast.expr | None:
    return next(
        (keyword.value for keyword in call.keywords if keyword.arg == name),
        None,
    )


def skill_contract(contract: Contract) -> None:
    pickup_digest = hashlib.sha256(PICKUP_PATH.read_bytes()).hexdigest()
    contract.check(
        pickup_digest == FROZEN_PICKUP_SHA256,
        "pickup_plate remains byte-identical to the UI-confirmed baseline",
    )

    source = PLACE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(PLACE_PATH))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "place_plate_at_testphyw"
    )
    constants = assignments(tree)
    args = [*function.args.posonlyargs, *function.args.args]
    contract.check(
        [arg.arg for arg in args] == ["plate", "openshelf"]
        and not function.args.defaults,
        "placement skill exposes only plate and openshelf inputs",
    )
    contract.check(
        constants.get("ARM") == "right_arm" and "left_arm" not in source,
        "placement uses only the right arm",
    )
    contract.check(
        constants.get("CARRY_GRASP_ANCHOR") == "horizontal_grip",
        "placement retains the verified horizontal_grip anchor",
    )
    contract.check(
        "SHELF_PREPOSE_ANCHOR" not in constants
        and constants.get("SHELF_RELEASE_ANCHOR") == "testphyw",
        "placement uses testphyw as its only shelf anchor",
    )
    contract.check(
        "ENTRY_CLEARANCE_M" not in constants
        and "TRANSIT_CLEARANCE_M" not in constants,
        "placement contains no derived transit-clearance sequence",
    )
    calls = [
        node for node in ast.walk(function) if isinstance(node, ast.Call)
    ]
    calls.sort(key=lambda node: (node.lineno, node.col_offset))
    call_names = [project_gate.call_name(node) for node in calls]
    tcp_index = call_names.index("get_object_tcp_transform")
    first_motion_index = next(
        index
        for index, name in enumerate(call_names)
        if name in {"move_arm", "move_arm_js", "set_gripper"}
    )
    contract.check(
        tcp_index < first_motion_index,
        "placement verifies the plate attachment before commanding motion",
    )
    joint_calls = [
        node for node in calls if project_gate.call_name(node) == "move_arm_js"
    ]
    contract.check(
        len(joint_calls) == 2
        and ast.unparse(keyword_value(joint_calls[0], "joint_angles"))
        == "RIGHT_FORWARD_FRONT"
        and ast.unparse(keyword_value(joint_calls[1], "joint_angles"))
        == "SECOND_TRANSITION_JOINTS",
        "placement runs the specified second joint move after RIGHT_FORWARD_FRONT",
    )
    contract.check(
        constants.get("SECOND_TRANSITION_JOINTS")
        == EXPECTED_SECOND_TRANSITION,
        "second placement joint target matches the requested six coordinates",
    )
    cartesian_calls = [
        node for node in calls if project_gate.call_name(node) == "move_arm"
    ]
    contract.check(
        len(cartesian_calls) == 1
        and all(
            keyword_value(call, "orientation") is not None
            and ast.unparse(keyword_value(call, "orientation"))
            == "carry['rpy']"
            for call in cartesian_calls
        ),
        "the direct placement move preserves the carried plate orientation",
    )
    contract.check(
        ast.unparse(keyword_value(cartesian_calls[0], "position"))
        == "release['xyz']",
        "the direct placement move targets testphyw position",
    )
    contract.check(
        "orientation=release[\"rpy\"]" not in source
        and "orientation=prepose[\"rpy\"]" not in source,
        "OpenShelf anchors never override the plate orientation",
    )

    detach_call = next(
        node
        for node in calls
        if project_gate.call_name(node) == "detach_object_from_arm"
    )
    snap_call = next(
        node
        for node in calls
        if project_gate.call_name(node)
        == "snap_object_anchor_to_world_pose"
    )
    contract.check(
        detach_call.lineno < snap_call.lineno,
        "placement detaches the plate before fixing its released world pose",
    )
    contract.check(
        len(snap_call.args) == 4
        and ast.unparse(snap_call.args[1]) == "CARRY_GRASP_ANCHOR"
        and ast.unparse(snap_call.args[2]) == "release['xyz']"
        and ast.unparse(snap_call.args[3]) == "carry['wxyz']",
        "released horizontal_grip snaps to testphyw position with carry orientation",
    )
    contract.check(
        constants.get("OPEN_GRIPPER_WIDTH_M", 0) > 0.06,
        "release opens wider than the verified plate grasp width",
    )
    contract.check(
        0 < constants.get("PLACE_SPEED", 0) <= 10,
        "direct placement uses a conservative positive speed",
    )
    contract.check(
        '"collision_planning_required": True' in source,
        "placement reports collision planning as required",
    )


def workflow_contract(contract: Contract) -> None:
    workflow = load_json(WORKFLOW_PATH)
    contract.check(
        workflow.get("simulation_validated") is False,
        "workflow remains unvalidated until cloud simulation succeeds",
    )
    contract.check(
        [item["name"] for item in workflow["inputs"]]
        == ["plate", "openshelf"],
        "workflow exposes the plate and OpenShelf objects",
    )
    skill_nodes = [
        node for node in workflow["nodes"] if node.get("type") == "skill"
    ]
    contract.check(
        [node.get("skill_id") for node in skill_nodes]
        == ["pickup_plate", "place_plate_at_testphyw"],
        "workflow runs the frozen pickup before the new placement",
    )
    contract.check(
        skill_nodes[0].get("parameters")
        == {"target": {"$input": "plate"}}
        and skill_nodes[1].get("parameters")
        == {
            "plate": {"$input": "plate"},
            "openshelf": {"$input": "openshelf"},
        },
        "workflow binds both skill nodes to shared object inputs",
    )
    edges = {
        (edge["from_node"], edge["to_node"]): edge["condition"]["type"]
        for edge in workflow["edges"]
    }
    contract.check(
        edges
        == {
            ("start_0", "pickup_plate"): "default",
            ("pickup_plate", "place_plate_at_testphyw"): "on_success",
            ("place_plate_at_testphyw", "end_1"): "on_success",
        },
        "workflow advances to placement only after a successful pickup",
    )
    project = load_json(PROJECT_PATH)
    contract.check(
        project.get("active_workflow") == EXPECTED_WORKFLOW
        and project.get("active_world") == EXPECTED_WORLD,
        "project activates the full workflow in openshelf_sucess",
    )


def geometry_contract(contract: Contract) -> None:
    plate_model = load_yaml(PLATE_MODEL_PATH)
    shelf_model = load_yaml(SHELF_MODEL_PATH)
    carry = plate_model["anchors"].get("horizontal_grip")
    release = shelf_model["anchors"].get("testphyw")
    contract.check(carry is not None, "plate model contains horizontal_grip")
    contract.check(release is not None, "OpenShelf model contains testphyw")
    if carry is not None:
        grasp = carry.get("grasp", {})
        contract.check(
            carry.get("parent_link") == "body"
            and grasp.get("width") == 0.06
            and grasp.get("standoff", 0) > 0,
            "horizontal_grip retains its body-relative grasp geometry",
        )
    if release is not None:
        release_xyz = release["link_T_anchor"]["xyz"]
        contract.check(
            len(release_xyz) == 3
            and all(math.isfinite(value) for value in release_xyz),
            "testphyw has a finite destination position",
        )

    world = load_json(WORLD_PATH)
    named_objects: dict[str, list[dict[str, Any]]] = {}
    for obj in world["objects"].values():
        name = obj.get("metadata", {}).get("name")
        if name:
            named_objects.setdefault(name, []).append(obj)
    for name in ("wellplate_pcr", "wellplate_holder_tags", "openshelf"):
        contract.check(
            len(named_objects.get(name, [])) == 1,
            f"openshelf_sucess contains exactly one {name}",
        )
        if len(named_objects.get(name, [])) == 1:
            contract.check(
                named_objects[name][0].get("collide_in_planner") is True,
                f"{name} collision planning is enabled",
            )


def main() -> int:
    print("End-to-end plate-to-testphyw verification")
    contract = Contract()
    try:
        skill_contract(contract)
        workflow_contract(contract)
        geometry_contract(contract)
    except (
        KeyError,
        StopIteration,
        ValueError,
        OSError,
        json.JSONDecodeError,
    ) as exc:
        contract.errors.append(str(exc))
        print(f"ERROR contract checker could not complete: {exc}")

    print()
    print(f"Result: {contract.checks} checks, {len(contract.errors)} error(s)")
    print(
        "This static contract does not prove right-arm IK or collision clearance. "
        "Run move_plate_to_openshelf_testphyw in openshelf_sucess cloud simulation."
    )
    return 1 if contract.errors else 0


if __name__ == "__main__":
    sys.exit(main())
