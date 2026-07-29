#!/usr/bin/env python3
"""Local verification loop for this Zeon project.

The checker protects the pipette demo golden reference, validates Zeon source
formats and cross-file contracts, and applies stricter authoring checks to files
currently changed in the Zeon working tree. It intentionally does not execute a
robot or claim that static checks prove IK, collision, or grasp safety.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
GOLDEN_MANIFEST = ROOT / "verification" / "golden_pipette_demo.json"
GOLDEN_SKILLS = (
    "epipette_grab",
    "epipette_attach",
    "epipette_aspirate",
    "epipette_dispense",
    "epipette_eject",
    "epipette_place",
)
REQUIRED_GOLDEN_PATHS = {
    "canvas/pipette_demo_screen.tsx",
    "skills/utils.py",
    "workflows/pipette_demo.json",
    "worlds/pipette_demo_world/live_state.yaml",
    "worlds/pipette_demo_world/world_state.json",
    *{
        f"skills/{skill_id}/{filename}"
        for skill_id in GOLDEN_SKILLS
        for filename in ("metadata.yaml", "modules.py", "robotic_code.py")
    },
}
WATCH_ROOTS = (
    ROOT / "CLAUDE.md",
    ROOT / "project.json",
    ROOT / "skills",
    ROOT / "workflows",
    ROOT / "worlds",
    ROOT / "objects",
    ROOT / "verification",
)

RUBY_YAML_TO_JSON = """
input = STDIN.read
data = YAML.safe_load(input, permitted_classes: [], aliases: true)
STDOUT.write(JSON.generate(data))
"""


@dataclass
class Reporter:
    checks: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def passed(self, message: str) -> None:
        self.checks += 1
        print(f"PASS  {message}")

    def error(self, message: str) -> None:
        self.errors.append(message)
        print(f"ERROR {message}")

    def warning(self, message: str) -> None:
        self.warnings.append(message)
        print(f"WARN  {message}")


@dataclass(frozen=True)
class SkillSignature:
    allowed: frozenset[str]
    required: frozenset[str]


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path, reporter: Reporter) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        reporter.error(f"{relative(path)} is missing")
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        reporter.error(f"{relative(path)} is not valid JSON: {exc}")
    return None


def load_yaml(path: Path, reporter: Reporter) -> Any | None:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        reporter.error(f"{relative(path)} is missing")
        return None
    except (OSError, UnicodeError) as exc:
        reporter.error(f"cannot read {relative(path)}: {exc}")
        return None

    try:
        result = subprocess.run(
            ["ruby", "-ryaml", "-rjson", "-e", RUBY_YAML_TO_JSON],
            input=text,
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        reporter.error(
            "Ruby is required for structured YAML validation but is unavailable"
        )
        return None

    if result.returncode != 0:
        detail = result.stderr.strip() or "unknown YAML parser error"
        reporter.error(f"{relative(path)} is not valid YAML: {detail}")
        return None

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        reporter.error(f"YAML parser returned invalid JSON for {relative(path)}: {exc}")
        return None


def zeon_status(reporter: Reporter) -> dict[str, Any] | None:
    try:
        result = subprocess.run(
            ["zeon", "status", "--json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        reporter.warning("zeon CLI is unavailable; working-tree checks were skipped")
        return None

    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        reporter.warning(f"zeon status failed; working-tree checks were skipped: {detail}")
        return None

    try:
        status = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        reporter.warning(f"zeon status returned invalid JSON: {exc}")
        return None

    if status.get("merge_in_progress"):
        reporter.error("Zeon merge is in progress; resolve or abort it before verification")
    if status.get("unmerged"):
        reporter.error(
            "unmerged Zeon paths: " + ", ".join(sorted(status["unmerged"]))
        )
    return status


def changed_paths(status: dict[str, Any] | None) -> set[str]:
    if status is None:
        return set()
    paths: set[str] = set()
    for key in ("added", "modified", "deleted", "unmerged"):
        paths.update(str(path) for path in status.get(key, []))
    return paths


def validate_golden(
    reporter: Reporter, status: dict[str, Any] | None
) -> tuple[dict[str, Any] | None, set[str]]:
    manifest = load_json(GOLDEN_MANIFEST, reporter)
    if not isinstance(manifest, dict):
        return None, set()
    if manifest.get("schema_version") != 1:
        reporter.error("golden manifest schema_version must be 1")

    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        reporter.error("golden manifest must contain a non-empty files mapping")
        return manifest, set()
    declared_paths = set(files)
    if declared_paths != REQUIRED_GOLDEN_PATHS:
        missing = sorted(REQUIRED_GOLDEN_PATHS - declared_paths)
        extra = sorted(declared_paths - REQUIRED_GOLDEN_PATHS)
        details = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if extra:
            details.append("unexpected " + ", ".join(extra))
        reporter.error("golden manifest path set changed: " + "; ".join(details))

    golden_paths: set[str] = set()
    mismatches: list[str] = []
    for raw_path, expected_digest in sorted(files.items()):
        if not isinstance(raw_path, str) or not isinstance(expected_digest, str):
            reporter.error("golden manifest paths and digests must be strings")
            continue
        candidate = Path(raw_path)
        if candidate.is_absolute() or ".." in candidate.parts:
            reporter.error(f"unsafe path in golden manifest: {raw_path!r}")
            continue
        path = ROOT / candidate
        golden_paths.add(candidate.as_posix())
        if not path.is_file():
            mismatches.append(f"{raw_path} (missing)")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected_digest:
            mismatches.append(f"{raw_path} (hash changed)")

    if mismatches:
        reporter.error(
            "golden pipette demo drift detected: " + ", ".join(mismatches)
        )
    else:
        reporter.passed(
            f"golden pipette demo is byte-identical ({len(golden_paths)} files)"
        )

    changed = changed_paths(status)
    changed_golden = sorted(golden_paths.intersection(changed))
    if changed_golden:
        reporter.error(
            "golden paths appear in the Zeon working-tree diff: "
            + ", ".join(changed_golden)
        )
    else:
        reporter.passed("no golden path appears in the Zeon working-tree diff")

    validate_golden_semantics(manifest, reporter)
    return manifest, golden_paths


def validate_golden_semantics(manifest: dict[str, Any], reporter: Reporter) -> None:
    workflow_path = ROOT / "workflows" / "pipette_demo.json"
    workflow = load_json(workflow_path, reporter)
    if not isinstance(workflow, dict):
        return

    expected = manifest.get("expected_skill_sequence")
    actual = [
        node.get("skill_id")
        for node in workflow.get("nodes", [])
        if isinstance(node, dict) and node.get("type") == "skill"
    ]
    if actual != expected:
        reporter.error(
            f"pipette_demo skill sequence changed: expected {expected}, got {actual}"
        )
    else:
        reporter.passed("golden workflow retains its expected six-skill sequence")

    world = load_json(
        ROOT / "worlds" / "pipette_demo_world" / "world_state.json", reporter
    )
    if not isinstance(world, dict):
        return
    world_names = {
        obj.get("metadata", {}).get("name")
        for obj in world.get("objects", {}).values()
        if isinstance(obj, dict)
    }
    missing_defaults = []
    for item in workflow.get("inputs", []):
        if not isinstance(item, dict) or item.get("type") != "object":
            continue
        default = item.get("defaultValue")
        if default and default not in world_names:
            missing_defaults.append(f"{item.get('name')}={default}")
    if missing_defaults:
        reporter.error(
            "golden workflow object defaults missing from pipette_demo_world: "
            + ", ".join(missing_defaults)
        )
    else:
        reporter.passed("golden workflow object defaults exist in its saved world")

    validate_workflow(workflow_path, reporter)
    for skill_id in GOLDEN_SKILLS:
        validate_skill(
            ROOT / "skills" / skill_id / "robotic_code.py",
            reporter,
            strict=False,
        )
    validate_world(
        ROOT / "worlds" / "pipette_demo_world" / "world_state.json", reporter
    )
    tree = parse_python(ROOT / "skills" / "utils.py", reporter)
    if tree is not None:
        reporter.passed("golden skills/utils.py has valid Python syntax")


def parse_python(path: Path, reporter: Reporter) -> ast.Module | None:
    try:
        source = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        reporter.error(f"{relative(path)} is missing")
        return None
    except (OSError, UnicodeError) as exc:
        reporter.error(f"cannot read {relative(path)}: {exc}")
        return None
    try:
        return ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        reporter.error(
            f"{relative(path)} has invalid Python syntax at line {exc.lineno}: "
            f"{exc.msg}"
        )
        return None


def function_signature(
    skill_id: str, reporter: Reporter
) -> SkillSignature | None:
    path = ROOT / "skills" / skill_id / "robotic_code.py"
    tree = parse_python(path, reporter)
    if tree is None:
        return None
    function = next(
        (
            node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == skill_id
        ),
        None,
    )
    if function is None:
        reporter.error(f"{relative(path)} has no top-level function {skill_id}()")
        return None

    positional = [*function.args.posonlyargs, *function.args.args]
    defaults_start = len(positional) - len(function.args.defaults)
    allowed = {arg.arg for arg in positional}
    required = {arg.arg for arg in positional[:defaults_start]}

    for arg, default in zip(function.args.kwonlyargs, function.args.kw_defaults):
        allowed.add(arg.arg)
        if default is None:
            required.add(arg.arg)

    allowed.discard("self")
    required.discard("self")
    return SkillSignature(frozenset(allowed), frozenset(required))


def call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""


def literal_success_return(node: ast.Return, value: bool) -> bool:
    if not isinstance(node.value, ast.Dict):
        return False
    for key, item in zip(node.value.keys, node.value.values):
        if (
            isinstance(key, ast.Constant)
            and key.value == "success"
            and isinstance(item, ast.Constant)
            and item.value is value
        ):
            return True
    return False


def numeric_sequence(node: ast.AST) -> bool:
    return isinstance(node, (ast.List, ast.Tuple)) and bool(node.elts) and all(
        isinstance(item, ast.Constant)
        and isinstance(item.value, (int, float))
        and not isinstance(item.value, bool)
        for item in node.elts
    )


def validate_skill(path: Path, reporter: Reporter, strict: bool) -> None:
    errors_before = len(reporter.errors)
    tree = parse_python(path, reporter)
    if tree is None:
        return
    skill_id = path.parent.name
    functions = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    function = next((node for node in functions if node.name == skill_id), None)
    if function is None:
        reporter.error(f"{relative(path)} must define top-level {skill_id}()")
        return

    if strict:
        false_returns = [
            node
            for node in ast.walk(function)
            if isinstance(node, ast.Return) and literal_success_return(node, False)
        ]
        if false_returns:
            lines = ", ".join(str(node.lineno) for node in false_returns)
            reporter.error(
                f"{relative(path)} returns success=False at line(s) {lines}; "
                "raise an exception to fail a workflow node"
            )

        calls = [node for node in ast.walk(function) if isinstance(node, ast.Call)]
        has_step_start = any(
            call_name(call) == "print_log"
            and any(
                keyword.arg == "runlog_type"
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value == "step_start"
                for keyword in call.keywords
            )
            for call in calls
        )
        if not has_step_start:
            reporter.error(
                f"{relative(path)} needs print_log(..., runlog_type='step_start')"
            )

        has_success_return = any(
            isinstance(node, ast.Return) and literal_success_return(node, True)
            for node in ast.walk(function)
        )
        if not has_success_return:
            reporter.error(
                f"{relative(path)} needs a successful return payload with success=True"
            )

        for call in calls:
            name = call_name(call)
            for keyword in call.keywords:
                if (
                    name == "move_arm"
                    and keyword.arg == "position"
                    and numeric_sequence(keyword.value)
                ):
                    reporter.error(
                        f"{relative(path)}:{call.lineno} hardcodes a Cartesian "
                        "position; load geometry from an object anchor"
                    )
                if (
                    name == "move_arm_js"
                    and keyword.arg == "joint_angles"
                    and numeric_sequence(keyword.value)
                ):
                    reporter.error(
                        f"{relative(path)}:{call.lineno} hardcodes transition joints; "
                        "use a named constant from a shared utility module"
                    )

    if len(reporter.errors) == errors_before:
        reporter.passed(
            f"{relative(path)} has valid Python and a matching {skill_id}() entry point"
        )


def input_references(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        if set(value) == {"$input"} and isinstance(value["$input"], str):
            yield value["$input"]
        else:
            for child in value.values():
                yield from input_references(child)
    elif isinstance(value, list):
        for child in value:
            yield from input_references(child)


def graph_reachable(start_ids: set[str], adjacency: dict[str, set[str]]) -> set[str]:
    seen: set[str] = set()
    pending = list(start_ids)
    while pending:
        node_id = pending.pop()
        if node_id in seen:
            continue
        seen.add(node_id)
        pending.extend(adjacency.get(node_id, set()) - seen)
    return seen


def validate_workflow(path: Path, reporter: Reporter) -> None:
    errors_before = len(reporter.errors)
    workflow = load_json(path, reporter)
    if not isinstance(workflow, dict):
        return

    workflow_id = workflow.get("workflow_id")
    if workflow_id != path.stem:
        reporter.error(
            f"{relative(path)} workflow_id must match filename {path.stem!r}"
        )

    raw_inputs = workflow.get("inputs")
    nodes = workflow.get("nodes")
    edges = workflow.get("edges")
    if not isinstance(raw_inputs, list):
        reporter.error(f"{relative(path)} inputs must be a list")
        return
    if not isinstance(nodes, list) or not isinstance(edges, list):
        reporter.error(f"{relative(path)} nodes and edges must be lists")
        return

    input_names = [
        item.get("name") for item in raw_inputs if isinstance(item, dict)
    ]
    if len(input_names) != len(set(input_names)) or any(
        not isinstance(name, str) or not name for name in input_names
    ):
        reporter.error(f"{relative(path)} has invalid or duplicate input names")
    declared_inputs = {name for name in input_names if isinstance(name, str)}

    node_ids = [
        node.get("node_id") for node in nodes if isinstance(node, dict)
    ]
    if len(node_ids) != len(nodes) or len(node_ids) != len(set(node_ids)):
        reporter.error(f"{relative(path)} has invalid or duplicate node_id values")
        return
    node_id_set = set(node_ids)
    start_ids = {
        node["node_id"]
        for node in nodes
        if isinstance(node, dict) and node.get("type") == "start"
    }
    end_ids = {
        node["node_id"]
        for node in nodes
        if isinstance(node, dict) and node.get("type") == "end"
    }
    if len(start_ids) != 1:
        reporter.error(f"{relative(path)} must have exactly one start node")
    if not end_ids:
        reporter.error(f"{relative(path)} must have at least one end node")

    forward = {node_id: set() for node_id in node_id_set}
    reverse = {node_id: set() for node_id in node_id_set}
    edge_ids: list[Any] = []
    for edge in edges:
        if not isinstance(edge, dict):
            reporter.error(f"{relative(path)} contains a non-object edge")
            continue
        edge_ids.append(edge.get("edge_id"))
        source = edge.get("from_node")
        target = edge.get("to_node")
        if source not in node_id_set or target not in node_id_set:
            reporter.error(
                f"{relative(path)} edge {edge.get('edge_id')!r} references "
                "a missing node"
            )
            continue
        forward[source].add(target)
        reverse[target].add(source)
    if len(edge_ids) != len(set(edge_ids)) or any(not edge_id for edge_id in edge_ids):
        reporter.error(f"{relative(path)} has invalid or duplicate edge_id values")

    reachable = graph_reachable(start_ids, forward)
    unreachable = sorted(node_id_set - reachable)
    if unreachable:
        reporter.error(
            f"{relative(path)} has nodes unreachable from start: "
            + ", ".join(unreachable)
        )
    can_finish = graph_reachable(end_ids, reverse)
    dead_ends = sorted(node_id_set - can_finish)
    if dead_ends:
        reporter.error(
            f"{relative(path)} has nodes with no path to an end: "
            + ", ".join(dead_ends)
        )

    for node in nodes:
        if not isinstance(node, dict) or node.get("type") != "skill":
            continue
        skill_id = node.get("skill_id")
        if not isinstance(skill_id, str) or not skill_id:
            reporter.error(
                f"{relative(path)} skill node {node.get('node_id')!r} "
                "has no skill_id"
            )
            continue
        signature = function_signature(skill_id, reporter)
        if signature is None:
            continue
        parameters = node.get("parameters", {})
        if not isinstance(parameters, dict):
            reporter.error(
                f"{relative(path)} node {node.get('node_id')!r} parameters "
                "must be an object"
            )
            continue
        supplied = set(parameters)
        unknown = sorted(supplied - signature.allowed)
        missing = sorted(signature.required - supplied)
        if unknown:
            reporter.error(
                f"{relative(path)} node {node.get('node_id')!r} supplies unknown "
                f"{skill_id} parameter(s): {', '.join(unknown)}"
            )
        if missing:
            reporter.error(
                f"{relative(path)} node {node.get('node_id')!r} omits required "
                f"{skill_id} parameter(s): {', '.join(missing)}"
            )
        refs = set(input_references(parameters))
        undeclared = sorted(refs - declared_inputs)
        if undeclared:
            reporter.error(
                f"{relative(path)} node {node.get('node_id')!r} references "
                f"undeclared workflow input(s): {', '.join(undeclared)}"
            )

    if len(reporter.errors) == errors_before:
        reporter.passed(
            f"{relative(path)} graph, skill signatures, and input bindings are valid"
        )


def finite_vector(
    value: Any, length: int, label: str, reporter: Reporter
) -> bool:
    valid = (
        isinstance(value, list)
        and len(value) == length
        and all(
            isinstance(item, (int, float))
            and not isinstance(item, bool)
            and math.isfinite(item)
            for item in value
        )
    )
    if not valid:
        reporter.error(f"{label} must contain {length} finite numbers")
    return valid


def validate_quaternion(value: Any, label: str, reporter: Reporter) -> None:
    if not finite_vector(value, 4, label, reporter):
        return
    norm = math.sqrt(sum(component * component for component in value))
    if not math.isclose(norm, 1.0, rel_tol=0.0, abs_tol=5e-3):
        reporter.error(f"{label} quaternion norm is {norm:.6f}, expected about 1")


def validate_object_model(path: Path, reporter: Reporter) -> None:
    errors_before = len(reporter.errors)
    model = load_yaml(path, reporter)
    if not isinstance(model, dict):
        return
    urdf = model.get("urdf")
    if not isinstance(urdf, str) or not urdf:
        reporter.error(f"{relative(path)} must declare a URDF filename")
    elif not (path.parent / urdf).is_file():
        reporter.error(f"{relative(path)} references missing URDF {urdf!r}")

    anchors = model.get("anchors")
    if not isinstance(anchors, dict) or not anchors:
        reporter.error(f"{relative(path)} must contain a non-empty anchors mapping")
        return
    for anchor_name, anchor in anchors.items():
        label = f"{relative(path)} anchor {anchor_name!r}"
        if not isinstance(anchor, dict):
            reporter.error(f"{label} must be an object")
            continue
        if not isinstance(anchor.get("parent_link"), str):
            reporter.error(f"{label} needs parent_link")
        transform = anchor.get("link_T_anchor")
        if not isinstance(transform, dict):
            reporter.error(f"{label} needs link_T_anchor")
            continue
        finite_vector(transform.get("xyz"), 3, f"{label} xyz", reporter)
        validate_quaternion(transform.get("wxyz"), f"{label} wxyz", reporter)
        grasp = anchor.get("grasp")
        if grasp is not None:
            if not isinstance(grasp, dict):
                reporter.error(f"{label} grasp must be an object")
                continue
            width = grasp.get("width")
            if (
                not isinstance(width, (int, float))
                or isinstance(width, bool)
                or width < 0
            ):
                reporter.error(f"{label} grasp width must be non-negative")
            standoff = grasp.get("standoff")
            if standoff is not None and (
                not isinstance(standoff, (int, float))
                or isinstance(standoff, bool)
                or standoff < 0
            ):
                reporter.error(f"{label} grasp standoff must be non-negative")

    if len(reporter.errors) == errors_before:
        reporter.passed(f"{relative(path)} has valid URDF and anchor structure")


def validate_metadata(path: Path, reporter: Reporter) -> None:
    errors_before = len(reporter.errors)
    metadata = load_yaml(path, reporter)
    if not isinstance(metadata, dict):
        return
    expected = path.parent.name
    if metadata.get("skill_id") != expected:
        reporter.error(
            f"{relative(path)} skill_id must match folder name {expected!r}"
        )
    elif len(reporter.errors) == errors_before:
        reporter.passed(f"{relative(path)} matches its skill folder")


def validate_world(path: Path, reporter: Reporter) -> None:
    errors_before = len(reporter.errors)
    world = load_json(path, reporter)
    if not isinstance(world, dict):
        return
    objects = world.get("objects")
    if not isinstance(objects, dict):
        reporter.error(f"{relative(path)} objects must be a mapping")
        return

    for object_id, obj in objects.items():
        label = f"{relative(path)} object {object_id!r}"
        if not isinstance(obj, dict):
            reporter.error(f"{label} must be an object")
            continue
        geometry = obj.get("geometry")
        if not isinstance(geometry, dict):
            reporter.error(f"{label} needs geometry")
            continue
        if geometry.get("type") == "articulated":
            yaml_path = geometry.get("yaml_path")
            if not isinstance(yaml_path, str) or not (ROOT / yaml_path).is_file():
                reporter.error(f"{label} references missing object model {yaml_path!r}")

        mount = obj.get("mount")
        if isinstance(mount, dict):
            pose = mount.get("world_P_body_fixed")
            if isinstance(pose, dict):
                finite_vector(pose.get("xyz"), 3, f"{label} pose xyz", reporter)
                validate_quaternion(
                    pose.get("wxyz"), f"{label} pose wxyz", reporter
                )
        collision = obj.get("collide_in_planner")
        if collision is not None and not isinstance(collision, bool):
            reporter.error(f"{label} collide_in_planner must be boolean")

    if len(reporter.errors) == errors_before:
        reporter.passed(
            f"{relative(path)} has valid object references, poses, and collision flags"
        )


def validate_project_manifest(path: Path, reporter: Reporter) -> None:
    errors_before = len(reporter.errors)
    project = load_json(path, reporter)
    if not isinstance(project, dict):
        return
    active_workflow = project.get("active_workflow")
    active_world = project.get("active_world")
    if active_workflow and not (ROOT / "workflows" / f"{active_workflow}.json").is_file():
        reporter.error(f"project.json active_workflow {active_workflow!r} is missing")
    if active_world and not (ROOT / "worlds" / str(active_world)).is_dir():
        reporter.error(f"project.json active_world {active_world!r} is missing")
    if len(reporter.errors) == errors_before:
        reporter.passed("project.json active workflow and world exist")


def validate_text(path: Path, reporter: Reporter) -> None:
    try:
        path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        reporter.error(f"cannot read {relative(path)} as UTF-8 text: {exc}")
        return
    reporter.passed(f"{relative(path)} is valid UTF-8 text")


def source_paths(changed_only: bool, changed: set[str]) -> list[Path]:
    if changed_only:
        return sorted(
            ROOT / path
            for path in changed
            if (ROOT / path).is_file()
        )

    paths: set[Path] = {ROOT / "project.json"}
    paths.update((ROOT / "workflows").glob("*.json"))
    paths.update((ROOT / "skills").glob("*/robotic_code.py"))
    paths.update((ROOT / "skills").glob("*/metadata.yaml"))
    paths.update((ROOT / "objects").glob("*/*.object_model.yaml"))
    paths.update((ROOT / "worlds").glob("*/world_state.json"))
    return sorted(path for path in paths if path.is_file())


def validate_sources(
    paths: Iterable[Path],
    changed: set[str],
    golden_paths: set[str],
    reporter: Reporter,
) -> None:
    validated = 0
    for path in paths:
        rel = relative(path)
        if rel in golden_paths:
            continue
        strict = rel in changed
        if path == ROOT / "project.json":
            validate_project_manifest(path, reporter)
        elif path.name == "robotic_code.py":
            validate_skill(path, reporter, strict=strict)
        elif path.name == "metadata.yaml" and path.parent.parent.name == "skills":
            validate_metadata(path, reporter)
        elif path.name.endswith(".object_model.yaml"):
            validate_object_model(path, reporter)
        elif path.parent.parent.name == "workflows" or path.parent.name == "workflows":
            validate_workflow(path, reporter)
        elif path.name == "world_state.json":
            validate_world(path, reporter)
        elif path.suffix == ".json":
            load_json(path, reporter)
        elif path.suffix in {".yaml", ".yml"}:
            load_yaml(path, reporter)
        elif path.suffix == ".py":
            parse_python(path, reporter)
        elif path.suffix in {".md", ".tsx"}:
            validate_text(path, reporter)
        validated += 1
    reporter.passed(f"validated {validated} non-golden project source files")


def run_once(changed_only: bool) -> int:
    print("Zeon project verification")
    print(f"root: {ROOT}")
    reporter = Reporter()
    status = zeon_status(reporter)
    changed = changed_paths(status)
    _, golden_paths = validate_golden(reporter, status)
    paths = source_paths(changed_only, changed)
    validate_sources(paths, changed, golden_paths, reporter)

    print()
    print(
        f"Result: {reporter.checks} checks, "
        f"{len(reporter.warnings)} warning(s), {len(reporter.errors)} error(s)"
    )
    print(
        "Static verification cannot prove IK, collision clearance, grasp quality, "
        "or hardware safety. Sync and run the intended workflow in cloud simulation."
    )
    return 1 if reporter.errors else 0


def watched_files() -> Iterable[Path]:
    for root in WATCH_ROOTS:
        if root.is_file():
            yield root
            continue
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if "__pycache__" in path.parts or "data" in path.parts:
                continue
            yield path


def snapshot() -> dict[str, tuple[int, int]]:
    result: dict[str, tuple[int, int]] = {}
    for path in watched_files():
        try:
            stat = path.stat()
        except FileNotFoundError:
            continue
        result[relative(path)] = (stat.st_mtime_ns, stat.st_size)
    return result


def watch(changed_only: bool, interval: float) -> int:
    print("Watching Zeon project files. Press Ctrl-C to stop.")
    run_once(changed_only)
    previous = snapshot()
    try:
        while True:
            time.sleep(interval)
            current = snapshot()
            if current == previous:
                continue
            previous = current
            print()
            print("=" * 72)
            print(time.strftime("Change detected at %Y-%m-%d %H:%M:%S"))
            run_once(changed_only)
    except KeyboardInterrupt:
        print("\nVerification watcher stopped.")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Protect the golden pipette demo and validate this Zeon project."
    )
    parser.add_argument(
        "--changed-only",
        action="store_true",
        help="validate only files changed in the Zeon working tree, plus the golden set",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="rerun verification whenever a project source file changes",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="watch polling interval in seconds (default: 1.0)",
    )
    args = parser.parse_args()
    if args.interval <= 0:
        parser.error("--interval must be positive")
    if args.watch:
        return watch(args.changed_only, args.interval)
    return run_once(args.changed_only)


if __name__ == "__main__":
    sys.exit(main())
