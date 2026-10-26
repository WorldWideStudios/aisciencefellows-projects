"""Quintic timing for joint moves and Cartesian pickup recipes.

Cartesian IK knots are joined with C1 cubic Hermite curves. Analytic polynomial
bounds limit joint speed/acceleration and travel, including between knots.
No collision, payload, force or motor dynamics model is included.
"""
import bisect
import math
import uuid

from .model import JOINTS, LIMITS, number, pose
from .kinematics import forward, orientation_error, solve, tangent

PICKUP_DEPTH = .003  # metres, base-frame -Z
CARTESIAN_TOLERANCE = 1e-6  # metres in the URDF model, not physical accuracy


def smoothstep(u):
    return u * u * u * (10 + u * (-15 + 6 * u))


def evaluate_curve(curve, progress):
    scaled = min(1., max(0., progress)) * len(curve)
    index = min(int(scaled), len(curve) - 1)
    u = scaled - index
    return {j: ((a * u + b) * u + c) * u + d for j, (a, b, c, d) in curve[index].items()}


def extrema(a, b, c):
    """Interior roots of 3a*u² + 2b*u + c (derivative of a cubic)."""
    if abs(a) < 1e-14:
        return [-c / (2 * b)] if abs(b) > 1e-14 else []
    discriminant = 4 * b * b - 12 * a * c
    if discriminant < 0:
        return []
    root = math.sqrt(discriminant)
    return [(-2 * b - root) / (6 * a), (-2 * b + root) / (6 * a)]


def pickup_curve(start, limits):
    origin, orientation = forward(start)
    displacement = (0., 0., -PICKUP_DEPTH)
    count = 30  # 0.1 mm IK spacing
    knots, derivatives = [start.copy()], [tangent(start, displacement)]
    for i in range(1, count + 1):
        target = (origin[0], origin[1], origin[2] - PICKUP_DEPTH * i / count)
        knots.append(solve(target, orientation, knots[-1], limits))
        derivatives.append(tangent(knots[-1], displacement))
    curve, velocity_bound, acceleration_bound = [], 0., 0.
    for i in range(count):
        piece = {}
        for joint in JOINTS:
            start_value, end_value = knots[i][joint], knots[i + 1][joint]
            first, last = derivatives[i][joint] / count, derivatives[i + 1][joint] / count
            delta = end_value - start_value
            a, b, c, d = first + last - 2 * delta, 3 * delta - 2 * first - last, first, start_value
            piece[joint] = (a, b, c, d)
            for u in (0., 1., *[u for u in extrema(a, b, c) if 0 < u < 1]):
                value = ((a * u + b) * u + c) * u + d
                if not limits[joint][0] - 1e-9 <= value <= limits[joint][1] + 1e-9:
                    raise ValueError(f"The 3 mm vertical path exceeds the {joint} joint limit")
            critical = [-b / (3 * a)] if abs(a) > 1e-14 else []
            velocity_bound = max(velocity_bound, *(abs(3*a*u*u + 2*b*u + c) * count
                                for u in (0., 1., *[u for u in critical if 0 < u < 1])))
            acceleration_bound = max(acceleration_bound, abs(2*b) * count**2, abs(6*a + 2*b) * count**2)
        curve.append(piece)
    # Check interpolated tool poses as well as IK endpoints. Reject paths whose
    # approximation would drift instead of silently reverting to a joint jog.
    for i in range(count * 4 + 1):
        progress = i / (count * 4)
        position, actual = forward(evaluate_curve(curve, progress))
        target = (origin[0], origin[1], origin[2] - PICKUP_DEPTH * progress)
        if math.dist(position, target) > CARTESIAN_TOLERANCE or max(map(abs, orientation_error(actual, orientation))) > 2e-5:
            raise ValueError("Cannot maintain a straight vertical tool path at this pose. Teach a different approach position.")
    return curve, knots[-1], velocity_bound, acceleration_bound


class Plan:
    def __init__(self, start, points, speed=20, acceleration=60, limits=None):
        try:
            self.start = pose(start, limits)
        except ValueError as exc:
            raise ValueError(f"Current start pose: {exc}") from exc
        if not points:
            raise ValueError("Add at least one sequence step before planning")
        self.speed = number(speed, "Speed", 1, 60)
        self.acceleration = number(acceleration, "Acceleration", 1, 120)
        self.id = str(uuid.uuid4())
        self.segments = []
        self.ends = []
        self.step_count = len(points)
        elapsed = 0.0
        previous = self.start
        for step_index, point in enumerate(points):
            kind = point.get("kind", "pose")
            if kind == "pickup_tip":
                try:
                    curve, bottom, q1, q2 = pickup_curve(previous, limits or LIMITS)
                except ValueError as exc:
                    raise ValueError(f"Pickup step '{point['name']}': {exc}") from exc
                # Chain rule: q_tt = q_ss*s_t² + q_s*s_tt. Polynomial bounds
                # cover the entire spline, including interpolation overshoot.
                duration = max(1., 1.875 * q1 / self.speed,
                               math.sqrt((1.875**2 * q2 + 10 / math.sqrt(3) * q1) / self.acceleration))
                for direction, start_pose, end_pose in (("down", previous, bottom), ("up", bottom, previous)):
                    self.segments.append({"kind": kind, "name": f"{point['name']} · {direction} 3 mm",
                                          "step_index": step_index, "from": start_pose.copy(), "to": end_pose.copy(),
                                          "start": elapsed, "move": duration, "dwell": 0.,
                                          "curve": curve, "reverse": direction == "up",
                                          "cartesian": {"frame": "base_link", "tool": "gripper_frame_link",
                                                        "delta_z_mm": -3 if direction == "down" else 3}})
                    elapsed += duration
                    self.ends.append(elapsed)
                # This action returns to exactly the preceding joint pose.
                continue
            if kind != "pose":
                raise ValueError("Unknown sequence step kind")
            try:
                target = pose(point["pose"], limits)
            except ValueError as exc:
                raise ValueError(f"Position '{point['name']}' ({point.get('source', 'unknown')}): {exc}") from exc
            distance = max(abs(target[j] - previous[j]) for j in JOINTS)
            # Max of s'(u) is 15/8; max |s''(u)| is 10/sqrt(3).
            duration = max(0.3, 1.875 * distance / self.speed,
                           math.sqrt((10 / math.sqrt(3)) * distance / self.acceleration))
            dwell = number(point.get("dwell", 0), "Dwell", 0, 30)
            self.segments.append({"name": point["name"], "step_index": step_index, "from": previous.copy(), "to": target,
                                  "start": elapsed, "move": duration, "dwell": dwell})
            elapsed += duration + dwell
            self.ends.append(elapsed)
            previous = target
        if elapsed > 600:
            raise ValueError("Sequence exceeds 10 minutes; shorten it or increase the speed")
        self.duration = elapsed

    def at(self, seconds):
        t = max(0, min(self.duration, seconds))
        index = min(bisect.bisect_right(self.ends, t), len(self.segments) - 1)
        segment = self.segments[index]
        u = min(1, max(0, (t - segment["start"]) / segment["move"]))
        s = smoothstep(u)
        if "curve" in segment:
            if u == 0:
                return segment["from"].copy(), index
            if u == 1:
                return segment["to"].copy(), index
            return evaluate_curve(segment["curve"], 1 - s if segment["reverse"] else s), index
        return {j: segment["from"][j] + (segment["to"][j] - segment["from"][j]) * s for j in JOINTS}, index

    def public(self):
        return {"id": self.id, "start": self.start, "duration": self.duration,
                "speed": self.speed, "acceleration": self.acceleration, "segments": self.segments,
                "step_count": self.step_count,
                "planner": "Quintic timing · joint positions + Cartesian pickup steps", "collision_checked": False}
