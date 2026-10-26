"""Launch LeRobot with filtered targets and bounded configuration-write retries."""
import argparse
import json
import math
import sys
import time

from so101_studio.filtering import TELEOP_RELATIVE_LIMITS, TargetFilter

from lerobot.motors.feetech import FeetechMotorsBus
import lerobot.scripts.lerobot_teleoperate as tele

_original_write = FeetechMotorsBus.write


def write_with_retries(self, data_name, motor, value, *, normalize=True, num_retry=0):
    return _original_write(
        self, data_name, motor, value,
        normalize=normalize, num_retry=max(num_retry, 3),
    )


def install_smoothing(tau, deadband, speed):
    original_loop = tele.teleop_loop

    def smooth_loop(*args, **kwargs):
        robot = kwargs['robot']
        get_observation, send_action = robot.get_observation, robot.send_action
        state = {}
        target_filter = TargetFilter(tau, deadband, speed)

        def observe():
            observation = get_observation()
            state.update(observation)
            return observation

        def send(action):
            filtered = target_filter.apply(action, state, time.perf_counter())
            sent = send_action(filtered)
            target_filter.accept(sent)
            return sent

        robot.get_observation, robot.send_action = observe, send
        try:
            return original_loop(*args, **kwargs)
        finally:
            robot.get_observation, robot.send_action = get_observation, send_action

    tele.teleop_loop = smooth_loop


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--smooth-tau', type=float, default=0.06)
    parser.add_argument('--smooth-deadband', type=float, default=0.2)
    parser.add_argument('--smooth-speed', type=float, default=80.0)
    options, remaining = parser.parse_known_args()
    for name, value in vars(options).items():
        if not math.isfinite(value) or value < 0 or (name == 'smooth_speed' and value == 0):
            parser.error(f'{name} must be finite and {"positive" if name == "smooth_speed" else "nonnegative"}')
    sys.argv[1:] = remaining
    FeetechMotorsBus.write = write_with_retries
    if not any(arg.startswith('--robot.max_relative_target') for arg in remaining):
        sys.argv.append('--robot.max_relative_target=' + json.dumps(TELEOP_RELATIVE_LIMITS, separators=(',', ':')))
    install_smoothing(options.smooth_tau, options.smooth_deadband, options.smooth_speed)
    tele.main()


if __name__ == '__main__':
    main()
