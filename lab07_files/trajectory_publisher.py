#!/usr/bin/env python3
"""
Arrival-Based Trajectory Publisher (ROS 2, rclpy)

Publishes a sequence of PoseStamped goals for a PID goal follower.
- Advances to the next waypoint when the drone is "arrived" (distance within tolerance
  for N consecutive odom messages).
- Optional time fallback via `max_hold_sec` in case of stalls.
- Keeps re-publishing the current goal at `repub_sec` so late subscribers catch it.

Run:
  # after sourcing your workspace
  ros2 run <your_pkg> trajectory_publisher

Useful parameters (all can be changed live with `ros2 param set`):
  repub_sec:       float (default 0.5)  -- re-publish cadence for the current goal
  loop:            bool  (default False) -- repeat the course when finished
  arrival_tol_m:   float (default 0.10) -- 3D distance threshold for arrival
  arrival_hits:    int   (default 5)    -- consecutive odom messages within tol to confirm arrival
  max_hold_sec:    float (default 0.0)  -- optional max dwell per waypoint (0.0 disables)

Notes:
- Uses /crazyflie/odom for current position. If your frames differ, ensure odom is in the same
  world/map frame you use for goals (a static map->odom identity is fine).
"""

# ========= IMPORTS =========
import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry

# ========= HELPER FUNCTIONS =========

def quat_from_yaw(yaw: float):
    """Return quaternion (x, y, z, w) for a pure Z rotation (yaw)."""
    half_yaw = 0.5 * float(yaw)
    return 0.0, 0.0, math.sin(half_yaw), math.cos(half_yaw)

# ========= MAIN ROS 2 NODE CLASS =========

class GoalPosePublisher(Node):
    def __init__(self):
        super().__init__('goal_pose_publisher')

        # --- Topics & frames (fixed for this lab) ---
        self.goal_topic = '/goal_pose'
        self.frame_id   = 'map'

        # --- Parameters ---
        self.declare_parameter('repub_sec', 0.5)
        self.declare_parameter('loop', False)
        self.declare_parameter('arrival_tol_m', 0.10)
        self.declare_parameter('arrival_hits', 5)
        self.declare_parameter('max_hold_sec', 0.0)  # 0.0 => disabled

        self.repub_sec      = float(self.get_parameter('repub_sec').value)
        self.loop           = bool(self.get_parameter('loop').value)
        self.arrival_tol_m  = float(self.get_parameter('arrival_tol_m').value)
        self.arrival_hits   = int(self.get_parameter('arrival_hits').value)
        self.max_hold_sec   = float(self.get_parameter('max_hold_sec').value)

        # --- Publisher ---
        self.pub = self.create_publisher(PoseStamped, self.goal_topic, 10)

        # --- Waypoints ---
        # Tuning Course (small cube) — default
        self.waypoints = [
            (0.0, 0.0, 0.50),   # 1. Takeoff to 0.5 m
            (0.5, 0.0, 0.50),   # 2. +X
            (0.5, 0.5, 0.50),   # 3. +Y
            (0.0, 0.5, 0.50),   # 4. -X
            (0.0, 0.0, 0.50),   # 5. back to start XY
            (0.0, 0.0, -0.05),  # 6. Land
        ]

        # Final Course (uncomment to use for the graded run)
        # self.waypoints = [
        #     (0.0, 0.0, 0.60, 0.0),
        #     (0.9, 0.0, 0.33, 0.0),
        #     (0.9, 0.9, 0.33, 0.0),
        #     (-0.9, 0.9, 0.33, 0.0),
        #     (-0.9, 0.9, 1.30, 0.0),
        #     (0.6, -1.0, 1.20, 0.0),
        #     (0.8, -1.0, 1.00, 0.0),
        #     (0.8, -0.5, 0.80, 0.0),
        #     (0.4, -0.5, 0.60, 0.0),
        #     (0.6, -1.0, 0.35, 0.0),
        #     (0.8, -1.0, 0.33, 0.0),
        #     (0.9, 0.9, 0.33, 0.0),
        #     (0.5, 0.9, 0.33, 0.0),
        #     (0.0, 0.0, 0.33, 0.0),
        #     (0.0, 0.0, -0.05, 0.0),
        # ]

        if not self.waypoints:
            self.get_logger().error("No waypoints to publish. Exiting.")
            raise SystemExit(1)

        # --- State ---
        self.idx = 0
        self.current_msg = None
        self.arrival_count = 0
        self.last_goal_time = self.get_clock().now()  # for optional max_hold_sec

        # --- Subscriptions & Timers ---
        self._odom_sub = self.create_subscription(Odometry, '/crazyflie/odom', self._odom_cb, 10)
        self.repub_timer = self.create_timer(self.repub_sec, self._republish_current_goal)

        # Kick off with the first goal
        self._publish_goal(self.idx)
        self.get_logger().info(
            f"Arrival-based trajectory: {len(self.waypoints)} wps | repub={self.repub_sec:.2f}s | "
            f"loop={self.loop} | tol={self.arrival_tol_m:.2f} m ({self.arrival_hits} hits) | "
            f"max_hold_sec={self.max_hold_sec:.1f} | frame='{self.frame_id}', topic='{self.goal_topic}'"
        )

    # --- Helpers ---

    def _publish_goal(self, i: int):
        """Build and publish PoseStamped for waypoint i."""
        wp = self.waypoints[i]
        x, y, z = wp[0], wp[1], wp[2]
        yaw = wp[3] if len(wp) > 3 else 0.0

        qx, qy, qz, qw = quat_from_yaw(yaw)

        msg = PoseStamped()
        msg.header.frame_id = self.frame_id
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.pose.position.x = float(x)
        msg.pose.position.y = float(y)
        msg.pose.position.z = float(z)
        msg.pose.orientation.x = qx
        msg.pose.orientation.y = qy
        msg.pose.orientation.z = qz
        msg.pose.orientation.w = qw

        self.pub.publish(msg)
        self.current_msg = msg
        self.arrival_count = 0
        self.last_goal_time = self.get_clock().now()

        self.get_logger().info(
            f"Goal {i+1}/{len(self.waypoints)}: x={x:.2f}, y={y:.2f}, z={z:.2f}, yaw={yaw:.2f}"
        )

    def _republish_current_goal(self):
        """Re-send the current goal with a fresh timestamp."""
        if self.current_msg is None:
            return
        self.current_msg.header.stamp = self.get_clock().now().to_msg()
        self.pub.publish(self.current_msg)

    # --- Arrival logic ---

    def _odom_cb(self, msg: Odometry):
        """Check distance to current goal; advance when within tolerance for N consecutive messages."""
        if self.current_msg is None:
            return

        # Current position from odom
        px = msg.pose.pose.position.x
        py = msg.pose.pose.position.y
        pz = msg.pose.pose.position.z

        # Current goal (x,y,z,yaw)
        gx = float(self.current_msg.pose.position.x)
        gy = float(self.current_msg.pose.position.y)
        gz = float(self.current_msg.pose.position.z)

        # 3D distance
        d = math.sqrt((gx - px)**2 + (gy - py)**2 + (gz - pz)**2)

        if d <= self.arrival_tol_m:
            self.arrival_count += 1
        else:
            self.arrival_count = 0

        # Optional time fallback to avoid getting stuck forever
        dwell_ok = False
        if self.max_hold_sec > 0.0:
            elapsed = (self.get_clock().now() - self.last_goal_time).nanoseconds * 1e-9
            dwell_ok = elapsed >= self.max_hold_sec

        if self.arrival_count >= self.arrival_hits or dwell_ok:
            self._advance_goal()

    def _advance_goal(self):
        """Advance to next waypoint (respect looping)."""
        self.idx += 1
        if self.idx >= len(self.waypoints):
            if not self.loop:
                self.get_logger().info("All goals reached. Done.")
                self.repub_timer.cancel()
                # keep node alive in case someone wants to introspect topics
                return
            self.idx = 0
            self.get_logger().info("Looping to start.")

        self._publish_goal(self.idx)

def main(args=None):
    rclpy.init(args=args)
    node = GoalPosePublisher()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()
