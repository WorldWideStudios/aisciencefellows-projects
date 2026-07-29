from .modules import capture_image, move_arm_js, print_log, set_gripper

# Captured left-arm joint-space trajectory (radians, 6-DOF), jogged and
# recorded by hand — not derived from anchors. Only valid for the arm
# configuration and world it was captured against (see
# docs/world_coordinates_training_plan.md for the tradeoff). TCP poses are
# kept as comments for reference only; they do not drive any motion here —
# the joint angles do.

# Step 1 — TCP (m, rad) [0.334, -0.276, 0.122, 2.235, 0.005, -0.677]
STEP_1_JOINTS = [-0.174, 0.310, -1.140, -0.773, 1.455, 0.853]
STEP_1_GRIPPER_M = 0.01

# Step 2 — TCP (m, rad) [0.305, -0.306, 0.121, 2.178, 0.029, -0.744]
STEP_2_JOINTS = [-0.246, 0.341, -1.144, -0.805, 1.485, 0.853]
STEP_2_GRIPPER_M = 0.0

# Step 3 — TCP (m, rad) [0.305, -0.306, 0.121, 2.178, 0.029, -0.743]
# Same pose as step 2 (a tighter re-grip in place, not a move).
STEP_3_JOINTS = [-0.246, 0.341, -1.144, -0.805, 1.485, 0.853]
# TODO: real close value is "position 18" in UFactory's own device units, not
# metres. That is NOT the same scale as width_m, and guessing a conversion
# here is exactly the mistake tacit/sessions/peel_seal/20-extracted.yaml
# warns against ("a plausible-looking width_m from an unchecked scale is the
# failure this session exists to prevent"). Holding at step 2's already-closed
# value (0.0) until the real conversion is measured against the arm.
STEP_3_GRIPPER_M = STEP_2_GRIPPER_M

# Step 4 — TCP (m, rad) [0.276, -0.360, 0.167, 2.343, -0.123, -0.951]
STEP_4_JOINTS = [-0.445, 0.183, -1.152, -0.749, 1.422, 0.853]

# Step 5 — TCP (m, rad) [0.240, -0.390, 0.177, 2.356, -0.146, -1.060]
STEP_5_JOINTS = [-0.552, 0.166, -1.163, -0.749, 1.422, 0.853]

# Step 6 — TCP (m, rad) [0.193, -0.424, 0.199, 2.383, -0.195, -1.198]
STEP_6_JOINTS = [-0.685, 0.126, -1.179, -0.750, 1.422, 0.853]

# Step 7 — TCP (m, rad) [0.151, -0.405, 0.242, 2.317, -0.169, -1.264]
STEP_7_JOINTS = [-0.686, 0.046, -1.178, -0.750, 1.580, 0.825]

# Step 8 (flip init) — TCP (m, rad) [0.145, -0.400, 0.238, -2.290, 0.030, 1.977]
# Wrist flips here: roll and yaw both cross over from step 7.
STEP_8_JOINTS = [-0.685, 0.046, -1.164, -0.749, 1.596, -2.476]

# Step 9 — TCP (m, rad) [0.258, -0.188, 0.080, -2.063, -0.456, 2.748]
STEP_9_JOINTS = [0.101, 0.338, -0.881, -0.749, 1.540, -2.476]

# Step 10 — same pose as step 9; this step is the release at that same point.
# TCP (m, rad) [0.258, -0.188, 0.080, -2.063, -0.456, 2.748]
STEP_10_JOINTS = [0.101, 0.338, -0.881, -0.749, 1.540, -2.476]
STEP_10_GRIPPER_M = 0.01

MOVE_SPEED = 0.3


def _snap(step: str):
    """Capture a still from the right arm's wrist camera (stationary — it's
    holding the plate — so these frames are directly comparable step to step,
    unlike the left arm's camera which changes framing with every waypoint).
    Never raises: capture_image handles its own errors and returns None on
    failure."""
    path = capture_image(arm="right_arm", capture_name=f"left_arm_pose_sequence_1_{step}", save_to_project=True)
    print_log(f"capture ({step}): {path}")


def left_arm_pose_sequence_1():
    """Move the left arm through the captured 10-waypoint sequence.

    Only ever commands the left arm — never touches the right arm, so
    whatever it is doing (e.g. holding a plate from a prior step) is left
    completely undisturbed. Gripper is only set at the waypoints an explicit
    width was given for (1, 2, 3, 10); steps 4-9 leave it untouched at
    whatever it was last set to. Captures a still from the right arm's
    (stationary) wrist camera after every waypoint.
    """
    print_log(runlog=True, runlog_type="step_start")
    print_log("Starting left_arm_pose_sequence_1")

    move_arm_js(arm="left_arm", joint_angles=STEP_1_JOINTS, speed=MOVE_SPEED)
    set_gripper(arm="left_arm", width_m=STEP_1_GRIPPER_M)
    _snap("step_1")

    move_arm_js(arm="left_arm", joint_angles=STEP_2_JOINTS, speed=MOVE_SPEED)
    set_gripper(arm="left_arm", width_m=STEP_2_GRIPPER_M)
    _snap("step_2")

    move_arm_js(arm="left_arm", joint_angles=STEP_3_JOINTS, speed=MOVE_SPEED)
    set_gripper(arm="left_arm", width_m=STEP_3_GRIPPER_M)
    _snap("step_3")

    move_arm_js(arm="left_arm", joint_angles=STEP_4_JOINTS, speed=MOVE_SPEED)
    _snap("step_4")

    move_arm_js(arm="left_arm", joint_angles=STEP_5_JOINTS, speed=MOVE_SPEED)
    _snap("step_5")

    move_arm_js(arm="left_arm", joint_angles=STEP_6_JOINTS, speed=MOVE_SPEED)
    _snap("step_6")

    move_arm_js(arm="left_arm", joint_angles=STEP_7_JOINTS, speed=MOVE_SPEED)
    _snap("step_7")

    print_log("left_arm_pose_sequence_1: step 8 (flip init)")
    move_arm_js(arm="left_arm", joint_angles=STEP_8_JOINTS, speed=MOVE_SPEED)
    _snap("step_8_flip_init")

    move_arm_js(arm="left_arm", joint_angles=STEP_9_JOINTS, speed=MOVE_SPEED)
    _snap("step_9")

    move_arm_js(arm="left_arm", joint_angles=STEP_10_JOINTS, speed=MOVE_SPEED)
    set_gripper(arm="left_arm", width_m=STEP_10_GRIPPER_M)
    _snap("step_10")

    print_log("left_arm_pose_sequence_1 completed")
    return {"success": True}
