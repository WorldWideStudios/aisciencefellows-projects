#!/usr/bin/env python3
"""Verify the focused right-arm horizontal plate pickup contract."""

from __future__ import annotations

import ast
import json
import math
import sys
from pathlib import Path
from typing import Any

import verify_zeon_project as project_gate


ROOT = Path(__file__).resolve().parents[1]
SKILL_PATH = ROOT / "skills" / "pickup_plate" / "robotic_code.py"
WORKFLOW_PATH = ROOT / "workflows" / "simulate_pickup_pcr_plate.json"
PLATE_MODEL_PATH = (
    ROOT / "objects" / "wellplate_pcr" / "wellplate_pcr.object_model.yaml"
)
PROJECT_PATH = ROOT / "project.json"
WORLD_PATH = ROOT / "worlds" / "openshelf_sucess" / "world_state.json"

EXPECTED_ARM = "right_arm"
EXPECTED_GRASP_ANCHOR = "horizontal_grip"
STALE_PICKUP_ANCHORS = {
    "side_grab",
    "horizontal_grip_authored_candidate",
}


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


def quaternion_multiply(first: list[float], second: list[float]) -> list[float]:
    aw, ax, ay, az = first
    bw, bx, by, bz = second
    return [
        aw * bw - ax * bx - ay * by - az * bz,
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
    ]


def normalize_quaternion(quaternion: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in quaternion))
    if norm <= 0:
        raise ValueError("quaternion must be non-zero")
    return [value / norm for value in quaternion]


def rotate_vector(quaternion: list[float], vector: list[float]) -> list[float]:
    normalized = normalize_quaternion(quaternion)
    conjugate = [
        normalized[0],
        -normalized[1],
        -normalized[2],
        -normalized[3],
    ]
    rotated = quaternion_multiply(
        quaternion_multiply(normalized, [0.0, *vector]),
        conjugate,
    )
    return rotated[1:]


def compose_pose(
    body_xyz: list[float],
    body_wxyz: list[float],
    local_xyz: list[float],
    local_wxyz: list[float],
) -> tuple[list[float], list[float]]:
    offset = rotate_vector(body_wxyz, local_xyz)
    world_xyz = [body_xyz[index] + offset[index] for index in range(3)]
    world_wxyz = normalize_quaternion(
        quaternion_multiply(
            normalize_quaternion(body_wxyz),
            normalize_quaternion(local_wxyz),
        )
    )
    return world_xyz, world_wxyz


def skill_contract(contract: Contract) -> None:
    source = SKILL_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(SKILL_PATH))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "pickup_plate"
    )

    assignments: dict[str, Any] = {}
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Constant)
        ):
            assignments[node.targets[0].id] = node.value.value

    args = [*function.args.posonlyargs, *function.args.args]
    contract.check(
        [arg.arg for arg in args] == ["target"] and not function.args.defaults,
        "pickup_plate exposes only the target object input",
    )
    contract.check(
        assignments.get("GRASP_ANCHOR") == EXPECTED_GRASP_ANCHOR,
        "pickup_plate fixes the grasp to horizontal_grip",
    )
    contract.check(
        assignments.get("ARM") == EXPECTED_ARM,
        "pickup_plate is assigned to the right arm",
    )
    contract.check(
        "left_arm" not in source,
        "pickup_plate contains no left-arm command",
    )
    contract.check(
        "[0.250, 0.112, -0.858, -1.347, 1.777, 2.382]" not in source,
        "pickup_plate contains no hardcoded transition joint list",
    )
    contract.check(
        "get_arm_pose" not in source
        and "current_pose" not in source
        and "high_pre_grasp" not in source,
        "pickup_plate contains no old-orientation or high-pregrasp sequence",
    )

    calls = [
        node
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
    ]
    calls.sort(key=lambda node: (node.lineno, node.col_offset))
    motion_names = {
        "move_arm",
        "move_arm_js",
        "move_relative",
        "set_gripper",
    }
    motion_calls = [
        node
        for node in calls
        if project_gate.call_name(node) in motion_names
    ]
    contract.check(
        bool(motion_calls)
        and project_gate.call_name(motion_calls[0]) == "move_arm_js",
        "first commanded motion is move_arm_js",
    )

    transition_call = next(
        (
            node
            for node in calls
            if project_gate.call_name(node) == "move_arm_js"
        ),
        None,
    )
    transition_target = None
    if transition_call is not None:
        transition_target = next(
            (
                keyword.value
                for keyword in transition_call.keywords
                if keyword.arg == "joint_angles"
            ),
            None,
        )
    contract.check(
        isinstance(transition_target, ast.Name)
        and transition_target.id == "RIGHT_FORWARD_FRONT",
        "joint transition uses RIGHT_FORWARD_FRONT",
    )

    snap_call = next(
        (
            node
            for node in calls
            if project_gate.call_name(node)
            == "snap_object_anchor_to_world_pose"
        ),
        None,
    )
    attach_call = next(
        (
            node
            for node in calls
            if project_gate.call_name(node) == "attach_object_to_arm"
        ),
        None,
    )
    contract.check(
        snap_call is not None
        and attach_call is not None
        and snap_call.lineno < attach_call.lineno,
        "canonical plate grip is asserted before attachment",
    )
    cartesian_calls = [
        node for node in calls if project_gate.call_name(node) == "move_arm"
    ]
    cartesian_orientations = [
        next(
            (
                keyword.value
                for keyword in node.keywords
                if keyword.arg == "orientation"
            ),
            None,
        )
        for node in cartesian_calls
    ]
    contract.check(
        len(cartesian_calls) == 2
        and all(
            orientation is not None
            and ast.unparse(orientation) == "grasp['rpy']"
            for orientation in cartesian_orientations
        ),
        "pre-grasp and grasp moves share the horizontal_grip orientation",
    )


def workflow_contract(contract: Contract) -> None:
    workflow = load_json(WORKFLOW_PATH)
    contract.check(
        [item["name"] for item in workflow["inputs"]] == ["plate"],
        "pickup workflow exposes only the plate input",
    )
    skill_nodes = [
        node for node in workflow["nodes"] if node.get("type") == "skill"
    ]
    contract.check(
        len(skill_nodes) == 1 and skill_nodes[0].get("skill_id") == "pickup_plate",
        "pickup workflow contains only the pickup_plate skill",
    )
    contract.check(
        skill_nodes
        and skill_nodes[0].get("parameters")
        == {"target": {"$input": "plate"}},
        "pickup workflow binds only the target parameter",
    )
    project = load_json(PROJECT_PATH)
    contract.check(
        project.get("active_world") == "openshelf_sucess",
        "project activates openshelf_sucess",
    )


def object_contract(contract: Contract) -> dict[str, Any]:
    plate_model = load_yaml(PLATE_MODEL_PATH)
    plate_anchors = plate_model["anchors"]
    grip = plate_anchors.get(EXPECTED_GRASP_ANCHOR)
    contract.check(grip is not None, "wellplate model contains horizontal_grip")
    if grip is not None:
        contract.check(
            grip.get("parent_link") == "body",
            "horizontal_grip is body-relative",
        )
        grasp = grip.get("grasp", {})
        contract.check(
            isinstance(grasp.get("width"), (int, float))
            and grasp["width"] > 0
            and isinstance(grasp.get("standoff"), (int, float))
            and grasp["standoff"] > 0,
            "horizontal_grip has positive width and standoff",
        )
        contract.check(
            grasp.get("gripper_variant") == "wellplate",
            "horizontal_grip selects the wellplate gripper variant",
        )
        approach_axis = rotate_vector(
            grip["link_T_anchor"]["wxyz"],
            [0.0, 0.0, 1.0],
        )
        contract.check(
            abs(approach_axis[2]) <= 1e-6,
            "horizontal_grip approach axis is horizontal",
        )
    for anchor_name in sorted(STALE_PICKUP_ANCHORS):
        contract.check(
            anchor_name not in plate_anchors,
            f"stale pickup anchor {anchor_name} is absent",
        )
    return plate_model


def world_contract(
    contract: Contract,
    plate_model: dict[str, Any],
) -> None:
    world = load_json(WORLD_PATH)
    named_objects: dict[str, list[dict[str, Any]]] = {}
    for obj in world["objects"].values():
        name = obj.get("metadata", {}).get("name")
        if name:
            named_objects.setdefault(name, []).append(obj)
    contract.check(
        len(named_objects.get("wellplate_pcr", [])) == 1,
        "openshelf_sucess contains exactly one wellplate_pcr",
    )
    contract.check(
        len(named_objects.get("wellplate_holder_tags", [])) == 1,
        "openshelf_sucess contains exactly one wellplate_holder_tags",
    )
    contract.check(
        len(named_objects.get("openshelf", [])) == 1,
        "openshelf_sucess contains exactly one openshelf",
    )
    plate = named_objects["wellplate_pcr"][0]
    holder = named_objects["wellplate_holder_tags"][0]
    openshelf = named_objects["openshelf"][0]
    collision_objects = {
        "wellplate": plate,
        "holder": holder,
        "openshelf": openshelf,
    }
    for label, obj in collision_objects.items():
        contract.check(
            obj.get("collide_in_planner") is True,
            f"{label} collision planning is enabled in openshelf_sucess",
        )

    plate_pose = plate["mount"]["world_P_body_fixed"]
    grip = plate_model["anchors"][EXPECTED_GRASP_ANCHOR]
    local_grip = grip["link_T_anchor"]
    grasp_world_xyz, grasp_world_wxyz = compose_pose(
        plate_pose["xyz"],
        plate_pose["wxyz"],
        local_grip["xyz"],
        local_grip["wxyz"],
    )
    approach_axis = rotate_vector(
        grasp_world_wxyz,
        [0.0, 0.0, 1.0],
    )
    standoff = grip["grasp"]["standoff"]
    pre_grasp_xyz = [
        grasp_world_xyz[index] - standoff * approach_axis[index]
        for index in range(3)
    ]
    contract.check(
        math.isclose(
            math.dist(grasp_world_xyz, pre_grasp_xyz),
            standoff,
            rel_tol=0.0,
            abs_tol=1e-9,
        ),
        "horizontal pre-grasp uses the anchor standoff distance",
    )
    contract.check(
        abs(grasp_world_xyz[2] - pre_grasp_xyz[2]) <= 1e-9,
        "horizontal pre-grasp preserves world height",
    )


def main() -> int:
    print("Focused pickup_plate verification")
    contract = Contract()
    try:
        skill_contract(contract)
        workflow_contract(contract)
        plate_model = object_contract(contract)
        world_contract(contract, plate_model)
    except (KeyError, StopIteration, ValueError, OSError, json.JSONDecodeError) as exc:
        contract.errors.append(str(exc))
        print(f"ERROR contract checker could not complete: {exc}")

    print()
    print(f"Result: {contract.checks} checks, {len(contract.errors)} error(s)")
    print(
        "This static contract does not prove right-arm IK or collision clearance. "
        "Run simulate_pickup_pcr_plate in openshelf_sucess cloud simulation."
    )
    return 1 if contract.errors else 0


if __name__ == "__main__":
    sys.exit(main())
