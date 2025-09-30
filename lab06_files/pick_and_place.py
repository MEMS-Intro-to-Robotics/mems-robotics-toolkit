#!/usr/bin/env python3
"""
Lab 6 — Pick & Place (Kinova Gen3 Lite)

Quick start:
  ros2 run lab06_moveit pick_and_place --ros-args -p task:=add_scene
"""

import threading
import time
from typing import Tuple

import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor

from geometry_msgs.msg import Pose
from pymoveit2 import MoveIt2
from pymoveit2.gripper_interface import GripperInterface


def make_pose(x: float, y: float, z: float) -> Pose:
    p = Pose()
    p.position.x, p.position.y, p.position.z = x, y, z
    p.orientation.w = 1.0  # identity quat
    return p


class PickAndPlaceNode(Node):
    def __init__(self):
        super().__init__("pick_and_place_node")

        # -------------------- MoveIt 2 (pymoveit2) --------------------
        self.moveit2 = MoveIt2(
            node=self,
            joint_names=["joint_1", "joint_2", "joint_3", "joint_4", "joint_5", "joint_6"],
            base_link_name="base_link",
            end_effector_name="end_effector_link",
            group_name="arm",
        )

        # -------------------- Gripper (pymoveit2) ---------------------
        try:
            self.gripper = GripperInterface(
                node=self,
                gripper_joint_names=["right_finger_bottom_joint"],
                open_gripper_joint_positions=[0.8],
                closed_gripper_joint_positions=[0.0],
                gripper_group_name="gripper",
                gripper_command_action_name="/gen3_lite_2f_gripper_controller/gripper_cmd",
            )
        except Exception as e:
            self.get_logger().warn(f"GripperInterface init failed ({e}); gripper actions skipped.")
            self.gripper = None

        # -------------------- Parameters (CLI-controlled) --------------
        self.declare_parameter("task", "none")
        self.declare_parameter("target_id", "block_1")

        # Joint presets
        self.joint_home = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        self.joint_retract = [0.0, -1.2, 1.4, 0.0, 1.1, 0.0]

    # ==================== Utilities ====================

    def move_joints(self, joints: list):
        self.moveit2.move_to_configuration(joint_positions=joints)
        self.moveit2.wait_until_executed()

    def move_cartesian_to(self, target_pose: Pose, fraction_ok: float = 0.90):
        traj = self.moveit2.plan(
            pose=target_pose, cartesian=True, max_step=0.005,
            cartesian_fraction_threshold=fraction_ok,
        )
        if traj is None:
            self.get_logger().warn("Cartesian plan rejected. Adjust pose / max_step.")
            return
        self.moveit2.execute(traj)
        self.moveit2.wait_until_executed()

    def open_gripper(self):
        if not self.gripper:
            self.get_logger().warn("No gripper available; open() skipped.")
            return
        self.gripper.open(); self.gripper.wait_until_executed()

    def close_gripper(self):
        if not self.gripper:
            self.get_logger().warn("No gripper available; close() skipped.")
            return
        self.gripper.close(); self.gripper.wait_until_executed()

    # ==================== Planning Scene helpers ======================

    def add_block(self, obj_id: str, size_xyz: Tuple[float, float, float], pose: Pose):
        self.moveit2.add_collision_box(
            id=obj_id,
            size=size_xyz,
            position=(pose.position.x, pose.position.y, pose.position.z),
            quat_xyzw=(pose.orientation.x, pose.orientation.y, pose.orientation.z, pose.orientation.w),
            frame_id=self.moveit2.base_link_name,
        )
        time.sleep(0.2)

    def remove_block(self, obj_id: str):
        # Safe to call even if it doesn't exist
        self.moveit2.remove_collision_object(id=obj_id)
        time.sleep(0.1)

    def clear_blocks_only(self):
        """Remove blocks but keep the table."""
        for oid in ("block_1", "block_2", "block_3"):
            self.remove_block(oid)
        self.get_logger().info("Cleared blocks (kept table).")

    # === §5.4: Add table + three blocks with correct RViz heights ===
    def add_table_and_blocks(self):
        # Always start clean so we never duplicate blocks
        self.clear_blocks_only()

        GAP = 0.001  # 1 mm below base plane
        TABLE_SIZE = (1.0, 1.0, 0.05)
        BLOCK_SIZE = (0.04, 0.04, 0.04)

        # Table center z = -GAP - thickness/2  → top sits just below 0
        table_center_z = -GAP - (TABLE_SIZE[2] / 2.0)
        self.add_block("table_top", TABLE_SIZE, make_pose(0.0, 0.0, table_center_z))

        # Blocks: default horizontal layout from Gazebo spawner
        X = 0.45
        SPACING = 0.08
        # Block center z = table top + half cube
        block_center_z = -GAP + (BLOCK_SIZE[2] / 2.0)

        self.add_block("block_1", BLOCK_SIZE, make_pose(X, -SPACING, block_center_z))
        self.add_block("block_2", BLOCK_SIZE, make_pose(X,  0.000,  block_center_z))
        self.add_block("block_3", BLOCK_SIZE, make_pose(X,  SPACING, block_center_z))

        self.get_logger().info("Added Planning Scene: table_top + block_1/2/3.")

    # ==================== Future milestones (stubs) ===================

    def gripper_sanity_check(self):
        self.get_logger().info("[TODO 5.5] Gripper sanity check placeholder.")

    def attach_block(self, obj_id: str):
        self.get_logger().info(f"[TODO 5.6] Would ATTACH '{obj_id}' to end_effector_link.")

    def detach_block(self, obj_id: str):
        self.get_logger().info(f"[TODO 5.6] Would DETACH '{obj_id}'.")

    def pick(self, obj_id: str, pre_grasp: Pose, grasp: Pose):
        self.get_logger().info(f"[TODO 5.9] pick('{obj_id}') placeholder.")

    def place(self, obj_id: str, pre_place: Pose, place: Pose):
        self.get_logger().info(f"[TODO 5.10] place('{obj_id}') placeholder.")

    def stack_three(self):
        self.get_logger().info("[TODO 5.11] stack_three() placeholder.")

    def attach_detach_demo(self, target_id: str = "block_1"):
        self.get_logger().info(f"[TODO 5.6] attach_detach_demo('{target_id}') placeholder.")


def main(args=None):
    rclpy.init(args=args)
    node = PickAndPlaceNode()

    # Keep services responsive while doing one-shot tasks
    exec = MultiThreadedExecutor(num_threads=2)
    exec.add_node(node)
    threading.Thread(target=exec.spin, daemon=True).start()

    # ---- NEW: move to HOME immediately (all zeros) ----
    node.get_logger().info("Moving to home (all joints = 0.0)…")
    node.move_joints(node.joint_home)

    # ---- NEW: clear blocks at startup (table kept) ----
    node.clear_blocks_only()

    # Dispatch tasks
    task = node.get_parameter("task").get_parameter_value().string_value
    target_id = node.get_parameter("target_id").get_parameter_value().string_value
    node.get_logger().info(f"Started with task='{task}', target_id='{target_id}'")

    try:
        if task == "none":
            node.get_logger().info("No task requested. Node is running.")
        elif task == "add_scene":
            node.add_table_and_blocks()
        elif task == "clear_blocks":
            node.clear_blocks_only()
        elif task == "gripper_check":
            node.gripper_sanity_check()
        elif task == "attach_detach_demo":
            node.attach_detach_demo(target_id=target_id)
        elif task == "stack_three":
            node.stack_three()
        else:
            node.get_logger().warn(f"Unknown task '{task}'. Nothing to do.")
    finally:
        time.sleep(0.3)
        rclpy.shutdown()


if __name__ == "__main__":
    main()
