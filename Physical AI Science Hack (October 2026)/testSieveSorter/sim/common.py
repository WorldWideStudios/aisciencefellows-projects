"""Types shared by the sorter sim modules. Units everywhere: mm, g, s."""
from dataclasses import dataclass, field
from typing import Callable

import numpy as np


def ellipse_fits(w, t, gap_w, gap_h, steps=91):
    """Whether a w x t elliptical cross-section passes a gap_w x gap_h opening at its best tilt.
    Flat grains pass square holes corner to corner: 2.0 x 1.7 mm rice fits a 2 mm square at 45 deg."""
    th = np.linspace(0.0, np.pi / 2, steps)
    a, b = w / 2, t / 2
    half_w = np.sqrt((a * np.cos(th)) ** 2 + (b * np.sin(th)) ** 2)
    half_h = np.sqrt((a * np.sin(th)) ** 2 + (b * np.cos(th)) ** 2)
    return bool(np.any((2 * half_w <= gap_w) & (2 * half_h <= gap_h)))


@dataclass
class Particle:
    """One grain or specimen, before it is placed in the scene.

    xml: children of a MuJoCo <body>: geoms, and optionally child <body> elements with hinge
    joints. No freejoint and no name or pos on the root; sorter.py wraps it as
    <body name=.. pos=.. quat=.. childclass="particle"><freejoint/>{xml}</body>. Child bodies
    must be named with the placeholder {p}, e.g. name="{p}_leg1", which becomes the particle name.
    Geom types: sphere, capsule, ellipsoid, cylinder, box. Each geom sets its own density and rgba.

    dims: "length" >= "width" >= "thickness" of the rigid body (for insects, without legs,
    antennae or wings), and "span", the largest extent including appendages. The particle fits
    in a sphere of radius span / 2 around the root origin.
    """
    kind: str
    group: str            # "grain" or "insect"
    xml: str
    dims: dict


@dataclass
class Design:
    """A sorter, in the tray frame: origin at the tray centre, z = 0 under the tray, x along the stroke.

    geoms: static geoms, each a MuJoCo primitive {"type": "box" | "capsule" | ..., "size": [...],
    "pos": [x, y, z], "quat": [w, x, y, z], "rgba": [r, g, b, a], "role": ...} or {"type": "mesh",
    "vertices": [[x, y, z], ...] (a convex solid, tray frame), "rgba": ..., "role": ...}.
    role is one of floor, wall, gate, screen, frame, lid. "lid" geoms collide but are not drawn.
    zones: [{"name": str, "box": [x0, x1, y0, y1, z0, z1]}] in flow order; a particle's zone is
    the first box containing its root body.
    spawn: [x0, x1, y0, y1, z0, z1] where particles are dropped in.
    ideal_zone: dims -> the zone name the particle would reach if every gate cut perfectly.
    jets_default: default spray jets for this design, as spray.Jet keyword dicts (lab frame).
    """
    name: str
    geoms: list
    zones: list
    spawn: list
    ideal_zone: Callable[[dict], str]
    stroke_axis: list = field(default_factory=lambda: [1.0, 0.0, 0.0])
    jets_default: list = field(default_factory=list)
    info: dict = field(default_factory=dict)
