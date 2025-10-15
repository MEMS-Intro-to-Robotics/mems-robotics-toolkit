#!/usr/bin/env python3
"""
Simple Trajectory Publisher (ROS 2, rclpy)

Publishes a sequence of PoseStamped goals for a PID goal follower.
- No TF or arrival checks; purely timing-based.
- Holds each goal for `hold_sec`, republishes every `repub_sec`.

How to run
After sourcing your workspace:
ros2 run <your_pkg> waypoint_publisher

On-the-fly Tuning
You can change parameters while this node is running! Open a new terminal and try:

# Make the drone hold each position for only 3.5 seconds
ros2 param set /goal_pose_publisher hold_sec 3.5

# Make the trajectory loop forever
ros2 param set /goal_pose_publisher loop True
"""

# ========= IMPORTS =========

# The 'math' library provides basic mathematical functions like sine and cosine.
import math
# 'rclpy' is the main Python library for interacting with ROS 2.
import rclpy
# 'Node' is the class we will inherit from to create our publisher node.
from rclpy.node import Node
# We import the 'PoseStamped' message type, which is what our controller node subscribes to.
from geometry_msgs.msg import PoseStamped

# ========= HELPER FUNCTIONS =========

def quat_from_yaw(yaw: float):
    """
    Return a quaternion (x, y, z, w) for a pure Z-axis rotation (yaw).
    In 3D robotics, rotations are often represented by quaternions to avoid issues
    like "gimbal lock". This function converts a simple yaw angle into that format.
    """
    # The math for converting a single yaw angle to a quaternion.
    half_yaw = 0.5 * float(yaw)
    # For a pure yaw rotation, the x and y components of the quaternion are always 0.
    return 0.0, 0.0, math.sin(half_yaw), math.cos(half_yaw)

    # ---
    # SUGGESTED IMPROVEMENT:
    # This function is great for yaw-only rotations. For more complex rotations involving
    # roll and pitch, you can use the `tf_transformations` library, which has a function:
    # `tf_transformations.quaternion_from_euler(roll, pitch, yaw)`
    # that handles all three axes.
    # ---

# ========= MAIN ROS 2 NODE CLASS =========

class GoalPosePublisher(Node):
    def __init__(self):
        """
        Constructor for the GoalPosePublisher node.
        This sets up the node, its parameters, publisher, and timers.
        """
        # Initialize the Node with the name 'goal_pose_publisher'.
        super().__init__('goal_pose_publisher')

        # --- Hardcoded Topics & Frames for this lab ---
        # Instead of using parameters, we set these values directly in the code for simplicity.
        self.goal_topic = '/goal_pose' # The topic to publish goal poses on.
        self.frame_id   = 'map'         # The coordinate frame for the goal poses.

        # --- Configurable Parameters ---
        # These settings can be changed from the command line when you run the node.
        self.declare_parameter('hold_sec', 10.0)     # How long to hold each waypoint goal.
        self.declare_parameter('repub_sec', 1.0)     # How often to re-publish the current goal.
        self.declare_parameter('loop', False)        # Whether to loop the trajectory when finished.

        # --- Resolve (get) the parameter values ---
        self.hold_sec   = float(self.get_parameter('hold_sec').value)
        self.repub_sec  = float(self.get_parameter('repub_sec').value)
        self.loop       = bool(self.get_parameter('loop').value)

        # --- Publisher ---
        # Create a publisher that sends PoseStamped messages on the specified topic.
        # The '10' is the queue size, which is how many messages to buffer.
        self.pub = self.create_publisher(PoseStamped, self.goal_topic, 10)

        # --- Waypoints ---
        # Each tuple represents a waypoint: (x, y, z, yaw_in_radians).

        # --- Tuning Waypoints (Simple Cube) ---
        # This is a simple course designed for tuning your PID controller.
        # It's a small box shape that is easy to observe and repeat.
        self.waypoints = [
            (0.0, 0.0, 0.5),   # 1. Takeoff to 0.5m
            (0.5, 0.0, 0.5),   # 2. Move forward 0.5m
            (0.5, 0.5, 0.5),   # 3. Move left 0.5m
            (0.0, 0.5, 0.5),   # 4. Move back 0.5m
            (0.0, 0.0, 0.5),   # 5. Return to start XY
            (0.0, 0.0, -0.05), # 6. Land
        ]

        # ---  Final Course Waypoints ---
        # Once your controller is well-tuned, comment out the "Tuning Waypoints" above
        # and uncomment this list to complete the required flight path.
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

        # ---
        # SUGGESTED IMPROVEMENT:
        # These waypoints are hardcoded. For a more advanced project, you could modify this node
        # to load waypoints from a file (e.g., a YAML or CSV file) using a ROS parameter.
        # ---

        # If after all that, we have no waypoints, it's an error. Exit.
        if not self.waypoints:
            self.get_logger().error("No waypoints to publish. Exiting.")
            raise SystemExit(1) # This stops the script.

        # --- State Variables ---
        self.idx = 0                  # The index of the current waypoint we are on.
        self.current_msg = None       # Stores the last message we published.

        # --- Timers ---
        # ROS timers call a function at a regular interval.
        # This timer calls `_republish_current_goal` to repeatedly send the same goal.
        self.repub_timer   = self.create_timer(self.repub_sec, self._republish_current_goal)
        # This timer calls `_advance_goal` to move to the next waypoint in the sequence.
        self.advance_timer = self.create_timer(self.hold_sec, self._advance_goal)

        # --- Kick off the sequence ---
        # Publish the very first goal immediately.
        self._publish_goal(self.idx)
        self.get_logger().info(
            f"Trajectory: {len(self.waypoints)} wps, hold={self.hold_sec:.1f}s, "
            f"repub={self.repub_sec:.1f}s, loop={self.loop}, frame='{self.frame_id}', topic='{self.goal_topic}'"
        )

    # --- Callback and Helper Methods ---

    def _publish_goal(self, i: int):
        """
        Constructs and publishes a PoseStamped message for the waypoint at index `i`.
        """
        # Get the waypoint data from our list.
        wp = self.waypoints[i]
        x, y, z = wp[0], wp[1], wp[2]
        # Use yaw if provided, otherwise default to 0.0.
        yaw = wp[3] if len(wp) > 3 else 0.0

        # Convert the yaw angle to a quaternion.
        qx, qy, qz, qw = quat_from_yaw(yaw)

        # Create a new PoseStamped message.
        msg = PoseStamped()
        # Fill in the header.
        msg.header.frame_id = self.frame_id
        msg.header.stamp = self.get_clock().now().to_msg()
        # Fill in the position.
        msg.pose.position.x = float(x)
        msg.pose.position.y = float(y)
        msg.pose.position.z = float(z)
        # Fill in the orientation (as a quaternion).
        msg.pose.orientation.x = qx
        msg.pose.orientation.y = qy
        msg.pose.orientation.z = qz
        msg.pose.orientation.w = qw

        # Publish the message.
        self.pub.publish(msg)
        # Store this message so the republish timer can use it.
        self.current_msg = msg
        self.get_logger().info(f"Goal {i+1}/{len(self.waypoints)}: x={x:.2f}, y={y:.2f}, z={z:.2f}, yaw={yaw:.2f}")

    def _republish_current_goal(self):
        """
        Timer callback to re-send the current goal message with an updated timestamp.
        """
        # If we haven't sent a goal yet, do nothing.
        if self.current_msg is None:
            return
        
        # Update the timestamp to the current time before publishing again.
        self.current_msg.header.stamp = self.get_clock().now().to_msg()
        self.pub.publish(self.current_msg)

    def _advance_goal(self):
        """
        Timer callback to advance to the next goal in the trajectory.
        """
        # Move to the next index.
        self.idx += 1
        
        # Check if we've finished the list of waypoints.
        if self.idx >= len(self.waypoints):
            # If looping is not enabled, we're done.
            if not self.loop:
                self.get_logger().info("All goals published. Done.")
                # Cancel the timers to stop all publishing.
                self.repub_timer.cancel()
                self.advance_timer.cancel()
                return
            
            # If looping is enabled, reset the index back to the beginning.
            self.idx = 0
            self.get_logger().info("Looping to start.")
        
        # Publish the new goal.
        self._publish_goal(self.idx)

        # ---
        # SUGGESTED IMPROVEMENT:
        # This node is purely time-based. It sends the next goal after `hold_sec` seconds,
        # regardless of whether the robot has actually reached the current goal.
        # A more robust system would subscribe to the robot's odometry or pose. It would then
        # check if the robot is close to `self.current_msg`. Only when the robot has "arrived"
        # would it call `_publish_goal` for the next waypoint. This makes the system independent
        # of how fast the controller is.
        # ---

def main(args=None):
    """
    The main function that sets up and runs the ROS 2 node.
    """
    # Initialize the rclpy library.
    rclpy.init(args=args)
    # Create an instance of our publisher node.
    node = GoalPosePublisher()
    try:
        # `spin` keeps the node alive and processing callbacks (like from timers).
        # It will block here until the node is shut down (e.g., by Ctrl+C).
        rclpy.spin(node)
    finally:
        # This code runs on shutdown. Cleanly destroy the node and shut down rclpy.
        node.destroy_node()
        rclpy.shutdown()

# This is a standard Python entry point.
# If this script is executed directly, the `main` function will be called.
if __name__ == "__main__":
    main()