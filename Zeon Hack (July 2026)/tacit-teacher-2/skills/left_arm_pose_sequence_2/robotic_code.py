from .modules import move_arm_js, print_log, set_gripper

# Captured left-arm joint-space trajectory v2 (radians, 6-DOF), jogged and
# recorded by hand — not derived from anchors. Only valid for the arm
# configuration and world it was captured against (see
# docs/world_coordinates_training_plan.md for the tradeoff). TCP poses are
# kept as comments for reference only; they do not drive any motion here —
# the joint angles do.
#
# Step numbering follows the capture session as given, with two gaps
# resolved: the unlabeled step between 2 and 4 is step 3, and the second
# "step 20" (labeled "final position") is renumbered step 21, since step 20
# is already "same pose as 19, gripper open to 0.01".

# Step 0 — TCP (m, rad) [0.334, -0.275, 0.122, 2.235, 0.005, -0.676]
STEP_0_JOINTS = [-0.174, 0.310, -1.140, -0.773, 1.455, 0.853]
STEP_0_GRIPPER_M = 0.01

# Step 1 — TCP (m, rad) [0.326, -0.284, 0.122, 2.234, 0.006, -0.704]
STEP_1_JOINTS = [-0.201, 0.310, -1.139, -0.773, 1.455, 0.853]

# Step 2 — TCP (m, rad) [0.313, -0.292, 0.115, 2.225, 0.023, -0.731]
STEP_2_JOINTS = [-0.228, 0.320, -1.129, -0.773, 1.455, 0.853]

# Step 3 (unlabeled in capture) — TCP (m, rad) [0.310, -0.298, 0.116, 2.220, 0.021, -0.739]
STEP_3_JOINTS = [-0.241, 0.322, -1.131, -0.780, 1.455, 0.853]

# Step 4 — TCP (m, rad) [0.306, -0.302, 0.115, 2.220, 0.023, -0.752]
STEP_4_JOINTS = [-0.257, 0.326, -1.131, -0.781, 1.452, 0.853]

# Step 5 — TCP (m, rad) [0.306, -0.304, 0.114, 2.220, 0.021, -0.751]
STEP_5_JOINTS = [-0.260, 0.326, -1.131, -0.784, 1.449, 0.853]

# Step 6 — same pose as step 5 (a re-grip in place, not a move). Gripper was
# observed at 0.019 m and set to 0.0 here.
STEP_6_JOINTS = STEP_5_JOINTS
STEP_6_GRIPPER_M = 0.0

# Step 7 — TCP (m, rad) [0.307, -0.304, 0.114, 2.220, 0.021, -0.750]
STEP_7_JOINTS = [-0.258, 0.326, -1.131, -0.784, 1.449, 0.853]

# Step 8 — TCP (m, rad) [0.308, -0.312, 0.133, 2.245, -0.024, -0.773]
STEP_8_JOINTS = [-0.280, 0.278, -1.134, -0.783, 1.449, 0.853]

# Step 9 — TCP (m, rad) [0.296, -0.325, 0.148, 2.456, -0.092, -0.987]
STEP_9_JOINTS = [-0.419, 0.181, -1.155, -0.629, 1.389, 0.853]

# Step 10 — TCP (m, rad) [0.285, -0.337, 0.157, 2.480, 0.156, -0.697]
STEP_10_JOINTS = [-0.462, 0.156, -1.155, -0.624, 1.389, 0.425]

# Step 11 — TCP (m, rad) [0.266, -0.361, 0.165, 2.518, 0.122, -0.797]
STEP_11_JOINTS = [-0.553, 0.145, -1.181, -0.593, 1.384, 0.425]

# Step 12 — TCP (m, rad) [0.248, -0.379, 0.190, 2.532, 0.065, -0.857]
STEP_12_JOINTS = [-0.614, 0.088, -1.183, -0.593, 1.384, 0.425]

# Step 13 — TCP (m, rad) [0.227, -0.396, 0.212, 2.545, 0.015, -0.916]
STEP_13_JOINTS = [-0.674, 0.036, -1.183, -0.593, 1.384, 0.425]

# Step 14 — TCP (m, rad) [0.215, -0.405, 0.234, 2.557, -0.035, -0.952]
STEP_14_JOINTS = [-0.709, -0.015, -1.183, -0.593, 1.384, 0.425]

# Step 15 — TCP (m, rad) [0.149, -0.384, 0.286, 2.522, -0.024, -1.091]
STEP_15_JOINTS = [-0.753, -0.144, -1.183, -0.593, 1.564, 0.425]

# Step 16 (Start Flip) — TCP (m, rad) [0.056, -0.293, 0.139, -2.260, -0.045, 1.661]
# Wrist flips here: roll and yaw cross over, j6 jumps from 0.425 to -2.188.
STEP_16_JOINTS = [-0.747, -0.007, -0.825, -0.593, 1.563, -2.188]

# Step 17 — TCP (m, rad) [0.253, -0.172, 0.052, -2.374, -0.104, 2.410]
STEP_17_JOINTS = [-0.080, 0.152, -0.794, -0.562, 1.305, -2.188]

# Step 18 — TCP (m, rad) [0.282, -0.160, 0.017, -2.469, -0.084, 2.463]
STEP_18_JOINTS = [-0.082, 0.209, -0.795, -0.563, 1.156, -2.188]

# Step 19 — TCP (m, rad) [0.312, -0.171, 0.008, -2.559, -0.022, 2.460]
STEP_19_JOINTS = [-0.136, 0.214, -0.807, -0.578, 1.042, -2.188]

# Step 20 — same pose as step 19; gripper opens to 0.01.
STEP_20_JOINTS = STEP_19_JOINTS
STEP_20_GRIPPER_M = 0.01

# Step 21 (final position) — TCP (m, rad) [0.400, -0.166, 0.187, -2.816, 0.377, 2.452]
STEP_21_JOINTS = [-0.095, -0.257, -0.807, -0.578, 1.042, -2.188]
STEP_21_GRIPPER_M = 0.019

MOVE_SPEED = 0.3


def left_arm_pose_sequence_2():
    """Move the left arm through the captured 22-waypoint sequence (v2).

    Only ever commands the left arm — never touches the right arm, so
    whatever it is doing (e.g. holding a plate from a prior step) is left
    completely undisturbed. Gripper is only set at the waypoints an explicit
    width was given for (0, 6, 20, 21); all other steps leave it untouched at
    whatever it was last set to.
    """
    print_log(runlog=True, runlog_type="step_start")
    print_log("Starting left_arm_pose_sequence_2")

    move_arm_js(arm="left_arm", joint_angles=STEP_0_JOINTS, speed=MOVE_SPEED)
    set_gripper(arm="left_arm", width_m=STEP_0_GRIPPER_M)

    move_arm_js(arm="left_arm", joint_angles=STEP_1_JOINTS, speed=MOVE_SPEED)

    move_arm_js(arm="left_arm", joint_angles=STEP_2_JOINTS, speed=MOVE_SPEED)

    move_arm_js(arm="left_arm", joint_angles=STEP_3_JOINTS, speed=MOVE_SPEED)

    move_arm_js(arm="left_arm", joint_angles=STEP_4_JOINTS, speed=MOVE_SPEED)

    move_arm_js(arm="left_arm", joint_angles=STEP_5_JOINTS, speed=MOVE_SPEED)

    move_arm_js(arm="left_arm", joint_angles=STEP_6_JOINTS, speed=MOVE_SPEED)
    set_gripper(arm="left_arm", width_m=STEP_6_GRIPPER_M)

    move_arm_js(arm="left_arm", joint_angles=STEP_7_JOINTS, speed=MOVE_SPEED)

    move_arm_js(arm="left_arm", joint_angles=STEP_8_JOINTS, speed=MOVE_SPEED)

    move_arm_js(arm="left_arm", joint_angles=STEP_9_JOINTS, speed=MOVE_SPEED)

    move_arm_js(arm="left_arm", joint_angles=STEP_10_JOINTS, speed=MOVE_SPEED)

    move_arm_js(arm="left_arm", joint_angles=STEP_11_JOINTS, speed=MOVE_SPEED)

    move_arm_js(arm="left_arm", joint_angles=STEP_12_JOINTS, speed=MOVE_SPEED)

    move_arm_js(arm="left_arm", joint_angles=STEP_13_JOINTS, speed=MOVE_SPEED)

    move_arm_js(arm="left_arm", joint_angles=STEP_14_JOINTS, speed=MOVE_SPEED)

    move_arm_js(arm="left_arm", joint_angles=STEP_15_JOINTS, speed=MOVE_SPEED)

    print_log("left_arm_pose_sequence_2: step 16 (start flip)")
    move_arm_js(arm="left_arm", joint_angles=STEP_16_JOINTS, speed=MOVE_SPEED)

    move_arm_js(arm="left_arm", joint_angles=STEP_17_JOINTS, speed=MOVE_SPEED)

    move_arm_js(arm="left_arm", joint_angles=STEP_18_JOINTS, speed=MOVE_SPEED)

    move_arm_js(arm="left_arm", joint_angles=STEP_19_JOINTS, speed=MOVE_SPEED)

    move_arm_js(arm="left_arm", joint_angles=STEP_20_JOINTS, speed=MOVE_SPEED)
    set_gripper(arm="left_arm", width_m=STEP_20_GRIPPER_M)

    move_arm_js(arm="left_arm", joint_angles=STEP_21_JOINTS, speed=MOVE_SPEED)
    set_gripper(arm="left_arm", width_m=STEP_21_GRIPPER_M)

    print_log("left_arm_pose_sequence_2 completed")
    return {"success": True}
