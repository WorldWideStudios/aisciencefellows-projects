"""URDF tool-frame kinematics and a small, dependency-free Cartesian IK solver.

Coordinates are metres in base_link, angles in radians internally. The tool is
gripper_frame_link, exactly as in the browser viewer. No hardware access.
"""
import math
import xml.etree.ElementTree as ET

from .model import JOINTS, URDF

ARM = JOINTS[:-1]
IDENTITY = ((1., 0., 0.), (0., 1., 0.), (0., 0., 1.))


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def mv(matrix, vector):
    return tuple(dot(row, vector) for row in matrix)


def mm(a, b):
    return tuple(tuple(dot(row, column) for column in zip(*b)) for row in a)


def rotation(axis, angle):
    x, y, z = axis
    c, s, v = math.cos(angle), math.sin(angle), 1 - math.cos(angle)
    return ((x*x*v+c, x*y*v-z*s, x*z*v+y*s),
            (y*x*v+z*s, y*y*v+c, y*z*v-x*s),
            (z*x*v-y*s, z*y*v+x*s, z*z*v+c))


def chain():
    parents = {j.find('child').attrib['link']: j for j in ET.parse(URDF).getroot().findall('joint')}
    link, result = 'gripper_frame_link', []
    while link in parents:
        joint = parents[link]
        origin = joint.find('origin')
        xyz = tuple(map(float, origin.attrib.get('xyz', '0 0 0').split()))
        roll, pitch, yaw = map(float, origin.attrib.get('rpy', '0 0 0').split())
        r = mm(mm(rotation((0, 0, 1), yaw), rotation((0, 1, 0), pitch)), rotation((1, 0, 0), roll))
        axis = tuple(map(float, joint.find('axis').attrib['xyz'].split()))
        result.append((joint.attrib['name'], xyz, r, axis, joint.attrib['type']))
        link = joint.find('parent').attrib['link']
    return tuple(reversed(result))


CHAIN = chain()


def forward_radians(q):
    position, orientation, axes = (0., 0., 0.), IDENTITY, []
    for name, xyz, origin, axis, kind in CHAIN:
        offset = mv(orientation, xyz)
        position = tuple(a + b for a, b in zip(position, offset))
        orientation = mm(orientation, origin)
        if kind != 'fixed':
            axes.append((position, mv(orientation, axis)))
            orientation = mm(orientation, rotation(axis, q[ARM.index(name)]))
    columns = [(*cross(axis, tuple(a - b for a, b in zip(position, center))), *axis)
               for center, axis in axes]
    return position, orientation, tuple(zip(*columns))


def forward(pose):
    """Return (tool XYZ in metres, tool rotation matrix) for a degree pose."""
    return forward_radians([math.radians(pose[j]) for j in ARM])[:2]


def orientation_error(current, target):
    columns = [cross(a, b) for a, b in zip(zip(*current), zip(*target))]
    return tuple(sum(c[i] for c in columns) / 2 for i in range(3))


def least_squares(jacobian, error):
    # Rotation residuals are scaled to a 100 mm lever arm. A tiny damping term
    # keeps near-singular solves bounded; reachability is checked independently.
    weights = (1., 1., 1., .1, .1, .1)
    rows = [[v * w for v in row] for row, w in zip(jacobian, weights)]
    rhs = [v * w for v, w in zip(error, weights)]
    columns = list(zip(*rows))
    a = [[dot(x, y) + (1e-12 if i == j else 0) for j, y in enumerate(columns)] + [dot(x, rhs)]
         for i, x in enumerate(columns)]
    n = len(a)
    for i in range(n):
        pivot = max(range(i, n), key=lambda k: abs(a[k][i]))
        a[i], a[pivot] = a[pivot], a[i]
        if abs(a[i][i]) < 1e-14:
            raise ValueError('Tool pose is singular; teach a less extended approach position')
        scale = a[i][i]
        a[i] = [v / scale for v in a[i]]
        for k in range(n):
            if k != i:
                scale = a[k][i]
                a[k] = [v - scale * x for v, x in zip(a[k], a[i])]
    return [a[i][-1] for i in range(n)]


def solve(target, orientation, seed, limits):
    q = [math.radians(seed[j]) for j in ARM]
    bounds = [tuple(map(math.radians, limits[j])) for j in ARM]
    blocked = set()
    for _ in range(60):
        position, actual, jacobian = forward_radians(q)
        delta = tuple(a - b for a, b in zip(target, position))
        angular = orientation_error(actual, orientation)
        if math.sqrt(dot(delta, delta)) < 2e-8 and math.sqrt(dot(angular, angular)) < 2e-7:
            return {**seed, **{j: math.degrees(v) for j, v in zip(ARM, q)}}
        step = least_squares(jacobian, (*delta, *angular))
        scale = min(1., .08 / max(max(map(abs, step)), 1e-12))
        for i, (lo, hi) in enumerate(bounds):
            proposed = q[i] + step[i] * scale
            if proposed < lo or proposed > hi:
                blocked.add(ARM[i])
            q[i] = min(hi, max(lo, proposed))
    detail = f" (joint limit: {', '.join(sorted(blocked))})" if blocked else ' (unreachable or near a singularity)'
    raise ValueError('Cannot complete the 3 mm vertical move while holding tool orientation' + detail +
                     '. Teach an approach pose with more joint travel available.')


def tangent(pose, displacement):
    """dq/ds for a Cartesian displacement over normalized path progress s."""
    _, _, jacobian = forward_radians([math.radians(pose[j]) for j in ARM])
    dq = least_squares(jacobian, (*displacement, 0., 0., 0.))
    return {**{j: math.degrees(v) for j, v in zip(ARM, dq)}, 'gripper': 0.}
