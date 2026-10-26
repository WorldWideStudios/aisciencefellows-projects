"""Shared command filter for the CLI launcher and browser teleoperation."""
import math

# Same relative target caps passed to LeRobot by teleoperate_arms.py. Arm units
# are calibrated degrees; the gripper uses percentage points.
TELEOP_RELATIVE_LIMITS = {
    "shoulder_pan": 10, "shoulder_lift": 10, "elbow_flex": 10,
    "wrist_flex": 20, "wrist_roll": 10, "gripper": 20,
}


def limit_relative_target(target, observation, limits=TELEOP_RELATIVE_LIMITS):
    """Match LeRobot's ensure_safe_goal_position without importing hardware."""
    if set(target) != set(observation) or set(target) != set(limits):
        raise ValueError("Relative target, feedback and limit joints must match")
    result = {}
    for joint, goal in target.items():
        present, cap = observation[joint], limits[joint]
        if not all(math.isfinite(v) for v in (goal, present, cap)) or cap <= 0:
            raise ValueError(f"Invalid relative target or feedback for {joint}")
        result[joint] = present + max(-cap, min(cap, goal - present))
    return result


class TargetFilter:
    """Time-based low-pass filter, deadband, and command slew limit.

    Values use LeRobot's calibrated position units (not necessarily degrees).
    Initialize from the follower and feed back the actually accepted targets.
    """

    def __init__(self, tau=0.06, deadband=0.2, speed=80.0):
        self.tau, self.deadband, self.speed = tau, deadband, speed
        self.previous = {}
        self.last_time = None

    def apply(self, action, observation, now):
        dt = 1 / 30 if self.last_time is None else min(max(now - self.last_time, 0), 1 / 30)
        self.last_time = now
        alpha = 1.0 if self.tau == 0 else -math.expm1(-dt / self.tau)
        result = dict(action)
        for key, target in action.items():
            if not key.endswith('.pos'):
                continue
            if not math.isfinite(target):
                raise ValueError(f'Non-finite target for {key}')
            previous = self.previous.get(key, observation.get(key))
            if previous is None or not math.isfinite(previous):
                raise ValueError(f'Missing finite follower position for {key}')
            delta = target - previous
            step = 0.0 if abs(delta) <= self.deadband else alpha * delta
            step = max(-self.speed * dt, min(self.speed * dt, step))
            result[key] = previous + step
        return result

    def accept(self, sent):
        self.previous.update({k: v for k, v in sent.items() if k.endswith('.pos')})

