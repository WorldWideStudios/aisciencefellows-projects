"""Teach the follower named positions with the leader, then replay routines on the follower alone.

  python arm/teach.py teach                       # follower mirrors the leader; save poses by name
  python arm/teach.py todo                        # which poses still need teaching
  python arm/teach.py run check rig/top           # dry run into a slot and back out, gripper open
  python arm/teach.py run pick rig/top            # take the filter out of a slot
  python arm/teach.py run pick rig/top A          # ...only if the wrist camera sees filter A (or F1) there
  python arm/teach.py run place storage/top       # put the held filter into a slot
  python arm/teach.py run move rig/top storage/top [FILTER]
  python arm/teach.py run scan                    # read every slot's marker: which filter is where
  python arm/teach.py run dump                    # grab the dish and pour it onto the top filter
  python arm/teach.py run goto NAME               # straight to one pose, no routing: check the path is clear
  python arm/teach.py inventory                   # which filter is in which slot, as last seen

Add --practice to try any command without the arm (it uses practice_poses.json, not your real poses;
the wrist camera is still used if it's plugged in). Ctrl+C stops a routine; the arm holds where it is.
"""
import argparse
import threading
import time

import motion
from motion import Arm, MissedGrab, MissingPose, WrongFilter

MIRROR_STEP = 2.0          # most a joint may move per mirror tick (degrees; gripper %), so jumps become glides
ROUTINES = "goto NAME | look SLOT | check SLOT | pick SLOT [FILTER] | place SLOT | move FROM TO [FILTER] | scan | dump"
TEACH_HELP = f"""Commands:
  save NAME         store the follower's current position as NAME (e.g. save rig/top/in)
  todo              poses the routines still need
  list              poses saved so far
  where             current joint positions
  delete NAME       remove a saved pose
  inventory         which filter is in which slot, as last seen
  {ROUTINES}
                    run on the follower (mirroring pauses; the leader is ignored).
                    look SLOT reads the marker from where the arm is now, e.g. at SLOT/front.
  follow            mirror the leader again (the follower glides over to it)
  quit"""


def practice_poses(layout):
    """Made-up poses for every required name, so routines can be tried without the arm."""
    poses = {}
    for i, name in enumerate(motion.required_poses(layout)):
        poses[name] = {j: float((i * 7 + k * 11) % 90 - 45) for k, j in enumerate(motion.JOINTS)}
    poses["gripper/open"]["gripper"] = 10.0
    poses["gripper/closed"]["gripper"] = 90.0
    return poses


def open_poses(practice, layout):
    path = motion.PRACTICE_POSES if practice else motion.POSES
    poses = motion.load_poses(path)
    if practice and not poses:
        poses = practice_poses(layout)
        motion.save_poses(poses, path)
    return path, poses


def pretend_grip(follower, args):
    """In practice mode the stand-in gripper stops on an object (60%), unless --practice-miss."""
    if args.practice:
        follower.object_at = None if args.practice_miss else 60.0


def routine(layout, words):
    """Steps for a command like ['move', 'rig/top', 'storage/top']."""
    cmd, args = words[0], words[1:]
    need = {"goto": (1, 1), "look": (1, 1), "check": (1, 1), "pick": (1, 2), "place": (1, 1), "move": (2, 3),
            "scan": (0, 0), "dump": (0, 0)}
    if cmd not in need or not need[cmd][0] <= len(args) <= need[cmd][1]:
        raise ValueError(f"usage: {ROUTINES}")
    if cmd in ("pick", "move") and len(args) == need[cmd][1]:
        args[-1] = motion.letter_for(args[-1], motion.load_filters())
    if cmd == "goto":
        return [["move", args[0]]]
    if cmd == "look":
        return [["look", args[0]]]
    if cmd == "check":
        return motion.check_steps(layout, args[0])
    if cmd == "pick":
        return motion.pick_steps(layout, *args)
    if cmd == "place":
        return motion.place_steps(layout, args[0])
    if cmd == "move":
        return motion.transfer_steps(layout, *args)
    if cmd == "scan":
        return motion.scan_steps(layout)
    return motion.dump_steps(layout)


def make_arm(follower, layout, poses, args):
    return Arm(follower, layout, poses, realtime=not args.practice, camera=motion.wrist_camera(layout),
               inventory_path=motion.PRACTICE_INVENTORY if args.practice else motion.INVENTORY)


def show_inventory(layout, inventory):
    filters = motion.load_filters()
    for slot in motion.all_slots(layout):
        seen = inventory["slots"]
        print(f"  {slot:16} {motion.filter_label(seen[slot], filters) if slot in seen else 'not checked'}")
    print(f"  {'holding':16} {motion.filter_label(inventory['holding'], filters) if inventory['holding'] else 'nothing'}")


def poses_needed(layout, steps, side=None):
    """Poses `steps` will use, starting on `side` (None: not at either shelf)."""
    carry = lambda s: layout["sides"][s]["carry"]
    names = []
    for step in steps:
        if step[0] == "move":
            names.append(step[1])
        elif step[0] in ("open", "close", "check_grip"):
            names += ["gripper/open", "gripper/closed"]
        elif step[0] == "side":
            names += ([carry(side)] if side not in (None, step[1]) else []) + [carry(step[1])]
            side = step[1]
        elif step[0] == "leave_side":
            names += [carry(side)] if side else []
            side = None
    return list(dict.fromkeys(names))


def run_routine(arm, steps):
    """Run steps; report how it ended instead of raising. Returns True if it finished."""
    try:
        arm.run(steps)
        print("Done.")
        return True
    except (MissedGrab, WrongFilter) as e:
        print(f"Stopped: {e}.")
    except MissingPose as e:
        print(f"Stopped: {e.args[0]}.")
    except KeyboardInterrupt:
        print("\nStopped (Ctrl+C). The arm is holding where it is.")
    return False


def cmd_run(args):
    layout = motion.load_layout()
    path, poses = open_poses(args.practice, layout)
    try:
        steps = routine(layout, args.words)
    except ValueError as e:
        raise SystemExit(str(e))
    missing = [n for n in poses_needed(layout, steps + motion.finish_steps()) if n not in poses]
    if missing:
        raise SystemExit(f"Teach these poses first: {', '.join(missing)}")

    follower, _ = motion.connect(args.follower_port, args.follower_id, practice=args.practice)
    pretend_grip(follower, args)
    arm = make_arm(follower, layout, poses, args)
    finished = run_routine(arm, steps)
    try:
        if finished:
            if not args.practice:
                input("Press Enter to go to 'rest' and switch the motors off (Ctrl+C keeps them on, holding).")
            run_routine(arm, motion.finish_steps())
        elif not args.practice:
            input("Support the arm with your hand, then press Enter to switch the motors off.")
        follower.disconnect()
    except KeyboardInterrupt:
        print("\nLeaving the motors on: the arm keeps holding its position.")


def cmd_todo(args):
    layout = motion.load_layout()
    _, poses = open_poses(args.practice, layout)
    missing = [n for n in motion.required_poses(layout) if n not in poses]
    print(f"{len(poses)} poses saved; still to teach ({len(missing)}): {', '.join(missing) or 'none'}")


def cmd_inventory(args):
    show_inventory(motion.load_layout(), motion.load_inventory(motion.PRACTICE_INVENTORY if args.practice
                                                                 else motion.INVENTORY))


def cmd_teach(args):
    layout = motion.load_layout()
    path, poses = open_poses(args.practice, layout)
    follower, leader = motion.connect(args.follower_port, args.follower_id, args.leader_port, args.leader_id,
                                      practice=args.practice)
    pretend_grip(follower, args)
    arm = make_arm(follower, layout, poses, args)
    lock = threading.Lock()
    state = {"mirror": True, "running": True, "errors": 0}

    def mirror():
        while state["running"]:
            tick = time.perf_counter()
            with lock:
                if state["mirror"]:
                    try:
                        target = {k.removesuffix(".pos"): v for k, v in leader.get_action().items()}
                        arm.send({j: arm.goal[j] + max(-MIRROR_STEP, min(MIRROR_STEP, target[j] - arm.goal[j]))
                                  for j in motion.JOINTS})
                    except (ConnectionError, OSError, RuntimeError):
                        state["errors"] += 1  # an occasional failed read is harmless; the next tick retries
            motion.sleep_until(tick + 1 / motion.RATE_HZ)

    thread = threading.Thread(target=mirror, daemon=True)
    thread.start()
    print("The follower now copies the leader.", "(practice mode: nothing moves)" if args.practice else "")
    print(TEACH_HELP)
    required = motion.required_poses(layout)
    while True:
        try:
            words = input("teach> ").split()
        except (EOFError, KeyboardInterrupt):
            words = ["quit"]
        if not words:
            continue
        cmd = words[0]
        if cmd == "save" and len(words) == 2:
            with lock:
                saved = {j: round(v, 2) for j, v in arm.goal.items()}
            poses[words[1]] = {**saved, "saved": time.strftime("%Y-%m-%d %H:%M")}
            motion.save_poses(poses, path)
            note = "" if words[1] in required else "  (no routine uses this name yet; fine if intended)"
            print(f"saved {words[1]}{note}")
        elif cmd == "delete" and len(words) == 2:
            print("deleted" if poses.pop(words[1], None) else "no such pose")
            motion.save_poses(poses, path)
        elif cmd == "list":
            print(", ".join(sorted(poses)) or "none yet")
        elif cmd == "todo":
            missing = [n for n in required if n not in poses]
            print(f"still to teach ({len(missing)}): {', '.join(missing) or 'none'}")
        elif cmd == "where":
            with lock:
                print("  ".join(f"{j} {v:.1f}" for j, v in arm.goal.items()))
        elif cmd == "inventory":
            show_inventory(layout, arm.inventory)
        elif cmd in ("goto", "look", "check", "pick", "place", "move", "scan", "dump"):
            try:
                steps = routine(layout, words)
            except ValueError as e:
                print(e)
                continue
            missing = [n for n in poses_needed(layout, steps, arm.side) if n not in poses]
            if missing:
                print(f"Teach these poses first: {', '.join(missing)}")
                continue
            if cmd == "look":  # only takes a photo, so the follower can keep copying the leader
                run_routine(arm, steps)
                continue
            with lock:
                state["mirror"] = False
            run_routine(arm, steps)
            print("Mirroring is paused. Type 'follow' to copy the leader again.")
        elif cmd == "follow":
            arm.side = None  # the leader can take the arm anywhere, so forget which side it's on
            with lock:
                state["mirror"] = True
            print("Following the leader.")
        elif cmd == "quit":
            break
        else:
            print(TEACH_HELP)

    try:
        if state["mirror"] and not args.practice:
            input("Put the LEADER in the rest position (the follower copies it), then press Enter. "
                  "The follower switches off after that.")
        elif not args.practice:
            input("Support the follower with your hand, then press Enter to switch it off.")
    except (EOFError, KeyboardInterrupt):
        pass
    state["running"] = False
    thread.join()
    leader.disconnect()
    follower.disconnect()
    if state["errors"]:
        print(f"({state['errors']} leader reads failed and were retried)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--practice", action="store_true", help="no arm: stand-ins, practice_poses.json")
    ap.add_argument("--practice-miss", action="store_true", help="practice mode: the gripper closes on nothing")
    ap.add_argument("--follower-port", default="COM6")
    ap.add_argument("--follower-id", default="my_follower")
    ap.add_argument("--leader-port", default="COM5")
    ap.add_argument("--leader-id", default="my_leader")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("teach")
    sub.add_parser("todo")
    sub.add_parser("inventory")
    r = sub.add_parser("run")
    r.add_argument("words", nargs="+", help=ROUTINES)
    args = ap.parse_args()
    {"teach": cmd_teach, "todo": cmd_todo, "inventory": cmd_inventory, "run": cmd_run}[args.cmd](args)


if __name__ == "__main__":
    main()
