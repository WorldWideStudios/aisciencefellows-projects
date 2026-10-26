"""Five-second instrumented teleoperation using the existing motion limit."""
import json
import time
from pathlib import Path
from contextlib import redirect_stdout
import logging
import sys
from lerobot.motors.feetech import FeetechMotorsBus
import lerobot.scripts.lerobot_teleoperate as tele

out = Path('diagnostics')
out.mkdir(exist_ok=True)
records = []
original_write = FeetechMotorsBus.write

def retry_write(self, data_name, motor, value, *, normalize=True, num_retry=0):
    return original_write(self, data_name, motor, value, normalize=normalize, num_retry=max(num_retry, 3))
FeetechMotorsBus.write = retry_write
original_loop = tele.teleop_loop

def logged_loop(*args, **kwargs):
    leader, follower = kwargs['teleop'], kwargs['robot']
    get_action, get_obs, send = leader.get_action, follower.get_observation, follower.send_action
    state = {}
    def observation():
        t=time.perf_counter(); result=get_obs()
        state.update(observation=result, read_ms=(time.perf_counter()-t)*1000)
        return result
    def action():
        t=time.perf_counter(); result=get_action()
        state.update(leader=result, leader_read_ms=(time.perf_counter()-t)*1000)
        return result
    def send_action(value):
        t=time.perf_counter(); result=send(value)
        records.append(dict(state, t=time.perf_counter(), requested=value, sent=result, send_ms=(time.perf_counter()-t)*1000))
        return result
    leader.get_action, follower.get_observation, follower.send_action = action, observation, send_action
    print('Connected. Five-second recording starts in 3 seconds. Support the follower when it ends.', flush=True)
    time.sleep(3)
    print('MOVE THE LEADER NOW — recording for five seconds.', flush=True)
    try:
        with open(out/'loop.txt','w') as stream, redirect_stdout(stream):
            original_loop(*args, **kwargs)
    finally:
        (out/'teleop_5s.json').write_text(json.dumps(records, indent=2))
        print(f'Recording stopped: {len(records)} samples saved.', flush=True)
tele.teleop_loop = logged_loop
logging.basicConfig(filename=out/'teleop_5s.log',level=logging.INFO,force=True)
if __name__ == '__main__':
    tele.main()
