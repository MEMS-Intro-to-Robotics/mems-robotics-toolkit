#!/usr/bin/env python3
"""
Simple Trajectory Plotter (ROS 2, rclpy)

WHAT THIS NODE DOES
- Subscribes to /goal_pose (PoseStamped) to capture commanded goals.
- Uses TF to read actual pose: target_frame <- source_frame.
- Samples at a fixed rate and records time, actual XYZ, and goal XYZ.
- On exit (Ctrl+C) writes:
  1) CSV: time_s,x,y,z,gx,gy,gz
  2) xyz_timeplots.png (actual vs goal over time)
  3) xy_traj.png (XY path + goal markers)

WHY YOU NEED IT
- After tuning PID, you must show tracking performance. This node generates the figures + CSV.
"""

import atexit
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.time import Time
from rclpy.duration import Duration
from geometry_msgs.msg import PoseStamped
from tf2_ros import Buffer, TransformListener, TransformException

# Headless backend works in Docker/WSL
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


class SimplePlotter(Node):
    def __init__(self):
        super().__init__('trajectory_plotter')

        # ---------------- Parameters (override with --ros-args -p name:=value) ----------------
        self.declare_parameter('goal_topic', '/goal_pose')
        self.declare_parameter('target_frame', 'map')                     # world frame
        self.declare_parameter('source_frame', 'crazyflie/base_footprint')# robot body frame
        self.declare_parameter('sample_hz', 20.0)                         # sampling rate (Hz)
        self.declare_parameter('tf_timeout_sec', 0.10)                    # TF lookup timeout (s)
        self.declare_parameter('csv_path', 'trajectory_log.csv')          # output CSV
        self.declare_parameter('save_figs', True)
        self.declare_parameter('fig_prefix', 'traj')

        # Resolve params
        self.goal_topic   = self.get_parameter('goal_topic').value
        self.target_frame = self.get_parameter('target_frame').value
        self.source_frame = self.get_parameter('source_frame').value
        self.sample_hz    = float(self.get_parameter('sample_hz').value)
        self.tf_timeout   = float(self.get_parameter('tf_timeout_sec').value)
        self.csv_path     = self.get_parameter('csv_path').value
        self.save_figs    = bool(self.get_parameter('save_figs').value)
        self.fig_prefix   = self.get_parameter('fig_prefix').value

        # ---------------- ROS interfaces ----------------
        self.tf_buf = Buffer()
        self.tf_listener = TransformListener(self.tf_buf, self)
        self.goal_sub = self.create_subscription(PoseStamped, self.goal_topic, self._on_goal, 10)

        # ---------------- State ----------------
        self.latest_goal = None
        self.t0 = self.get_clock().now()

        # Lists are fine for this lab size
        self.t, self.x, self.y, self.z = [], [], [], []     # measured
        self.gx, self.gy, self.gz = [], [], []              # goal

        # Sampling timer
        self.create_timer(1.0 / max(self.sample_hz, 1.0), self._sample_once)

        # Ensure saving on Ctrl+C
        atexit.register(self._finalize)

        self.get_logger().info(
            f"[plotter] goals: {self.goal_topic} | frames: {self.target_frame} <- {self.source_frame} | "
            f"rate: {self.sample_hz:.1f} Hz"
        )

    # ---------------- Callbacks ----------------
    def _on_goal(self, msg: PoseStamped):
        # Store latest goal as-is; your publisher/controller should use the same world frame.
        self.latest_goal = msg

    # ---------------- Sampling loop ----------------
    def _sample_once(self):
        try:
            tf = self.tf_buf.lookup_transform(
                self.target_frame, self.source_frame, Time(), timeout=Duration(seconds=self.tf_timeout)
            )
        except TransformException as ex:
            # No TF this tick (e.g., early startup) → skip sample
            self.get_logger().debug(f"TF miss ({self.target_frame} <- {self.source_frame}): {ex}")
            return

        now = self.get_clock().now()
        t_s = (now - self.t0).nanoseconds * 1e-9

        # Actual pose from TF
        px = tf.transform.translation.x
        py = tf.transform.translation.y
        pz = tf.transform.translation.z

        # Goal pose from /goal_pose (if none yet → zeros so plots start flat)
        if self.latest_goal is not None:
            gx = self.latest_goal.pose.position.x
            gy = self.latest_goal.pose.position.y
            gz = self.latest_goal.pose.position.z
        else:
            gx = gy = gz = 0.0

        # Append one row
        self.t.append(t_s); self.x.append(px); self.y.append(py); self.z.append(pz)
        self.gx.append(gx); self.gy.append(gy); self.gz.append(gz)

    # ---------------- Save results ----------------
    def _finalize(self):
        if not self.t:
            return  # nothing recorded

        # CSV
        arr = np.column_stack([self.t, self.x, self.y, self.z, self.gx, self.gy, self.gz])
        np.savetxt(self.csv_path, arr, delimiter=",", header="time_s,x,y,z,gx,gy,gz", comments="")
        self.get_logger().info(f"[plotter] saved CSV: {self.csv_path} ({arr.shape[0]} samples)")

        if not self.save_figs:
            return

        # Figure 1: X/Y/Z vs time
        fig1 = plt.figure(figsize=(9, 6))
        ax1 = fig1.add_subplot(3, 1, 1); ax2 = fig1.add_subplot(3, 1, 2); ax3 = fig1.add_subplot(3, 1, 3)
        ax1.plot(self.t, self.x, label="x (actual)"); ax1.plot(self.t, self.gx, linestyle="--", label="x (goal)")
        ax2.plot(self.t, self.y, label="y (actual)"); ax2.plot(self.t, self.gy, linestyle="--", label="y (goal)")
        ax3.plot(self.t, self.z, label="z (actual)"); ax3.plot(self.t, self.gz, linestyle="--", label="z (goal)")
        ax1.set_ylabel("x [m]"); ax2.set_ylabel("y [m]"); ax3.set_ylabel("z [m]"); ax3.set_xlabel("time [s]")
        ax1.legend(); ax2.legend(); ax3.legend()
        fig1.tight_layout()
        f1 = f"{self.fig_prefix}_xyz_timeplots.png"
        fig1.savefig(f1, dpi=150); plt.close(fig1)
        self.get_logger().info(f"[plotter] saved plot: {f1}")

        # Figure 2: XY path + goal markers
        xy = np.column_stack([self.x, self.y]); gxy = np.column_stack([self.gx, self.gy])
        if len(gxy) > 1:
            changes = np.any(gxy[1:] != gxy[:-1], axis=1)
            gxy_show = gxy[np.concatenate([[True], changes])]
        else:
            gxy_show = gxy

        fig2 = plt.figure(figsize=(6, 6))
        ax = fig2.add_subplot(1, 1, 1)
        ax.plot(xy[:, 0], xy[:, 1], label="path (actual)")
        if len(gxy_show) > 0:
            ax.scatter(gxy_show[:, 0], gxy_show[:, 1], marker="x", label="goals", zorder=5)
        ax.set_aspect('equal'); ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]")
        ax.grid(True, alpha=0.3); ax.legend()
        fig2.tight_layout()
        f2 = f"{self.fig_prefix}_xy_traj.png"
        fig2.savefig(f2, dpi=150); plt.close(fig2)
        self.get_logger().info(f"[plotter] saved plot: {f2}")


def main(args=None):
    rclpy.init(args=args)
    node = SimplePlotter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
