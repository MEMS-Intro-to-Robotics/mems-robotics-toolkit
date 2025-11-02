#!/usr/bin/env python3
"""
Lab 7 — 3D Goal Controller

Purpose (keep it simple)

Subscribe to a PoseStamped goal (e.g., /goal_pose).

Use TF to get the robot pose in a world frame (target_frame).

Compute PID in world (X/Y/Z) → rotate command into body → publish Twist.

Yaw control is intentionally disabled; you will NOT tune yaw in this lab.

Defaults

All PID gains for X/Y/Z default to 0.0 so this does nothing until you tune it.

How to run (example)
After sourcing your workspace, with sim running and TF available:

ros2 run <your_pkg> goal_3d_controller --ros-args 
-p kp_x:=0.6 -p kd_x:=0.12 
-p kp_y:=0.6 -p kd_y:=0.12 
-p kp_z:=1.2 -p kd_z:=0.25

Tuning hints

Start with P only. Raise kp_* until it moves briskly with limited overshoot.

Add a little D to tame oscillations. KI is usually small or zero for this task.

Keep max_v_* low at first (e.g., 0.5 m/s) then raise once it's stable.
"""

# ========= IMPORTS =========
# Import necessary libraries and message types.

# Allows for using type hints like 'PID' within the PID class itself.
from __future__ import annotations

# The 'math' library provides basic mathematical functions like sine and cosine.
import math
# 'Optional' is a type hint that means a variable can either be a certain type or 'None'.
from typing import Optional

# 'rclpy' is the main Python library for interacting with ROS 2.
import rclpy
# 'Node' is the class we will inherit from to create our controller node.
from rclpy.node import Node

# Import specific ROS message types that we will use for communication.
# PoseStamped: A position and orientation with a timestamp and coordinate frame. Used for goals.
# Twist: A message for linear (forward/back, left/right, up/down) and angular (roll, pitch, yaw) velocities. Used for motor commands.
# TransformStamped: Represents a coordinate frame transformation (translation and rotation).
from geometry_msgs.msg import PoseStamped, Twist, TransformStamped
# Odometry: A message that contains a robot's estimated pose and velocity.
from nav_msgs.msg import Odometry
# Duration and Time are used for handling time-related operations in ROS 2.
from rclpy.duration import Duration
from rclpy.time import Time

# TF2 is the ROS 2 library for managing coordinate transformations.
# Buffer: Stores incoming transforms and provides them on request.
# TransformListener: Subscribes to the /tf topic and populates the Buffer.
# TransformBroadcaster: Publishes transforms to the /tf topic.
from tf2_ros import Buffer, TransformListener, TransformBroadcaster, StaticTransformBroadcaster
# A very helpful library for converting between different rotation representations (like quaternions and Euler angles).
import tf_transformations  # for yaw from quaternion

# ========= HELPER FUNCTIONS =========
# These are small, reusable functions that help with math and transformations.

def wrap_pi(a: float) -> float:
    """
    Ensure an angle is within the range [-pi, pi].
    This is important for yaw angles to prevent them from growing infinitely large.
    For example, 3.15 radians becomes approximately -3.13 radians.
    """
    # atan2 is a clever way to handle all quadrants correctly and wrap the angle.
    return math.atan2(math.sin(a), math.cos(a))

    # ---
    # SUGGESTED IMPROVEMENT:
    # As an exercise, try to implement this function yourself using only `if` statements
    # and the `math.pi` constant, without using atan2.
    # ---

def quat_to_yaw(x: float, y: float, z: float, w: float) -> float:
    """
    Convert a quaternion (x, y, z, w) to a single yaw angle (rotation around Z-axis).
    Quaternions are used in ROS to represent 3D rotations without ambiguity.
    """
    # This function from the 'tf_transformations' library does the conversion for us.
    # It returns roll, pitch, and yaw. We only care about yaw, so we ignore the first two values.
    _, _, yaw = tf_transformations.euler_from_quaternion([x, y, z, w])
    return yaw

def rotate_world_to_body(vx_w: float, vy_w: float, yaw: float) -> tuple[float, float]:
    """
    Rotate a 2D velocity vector from the world frame to the robot's body frame.
    The robot's body frame has +x pointing forward and +y pointing left.
    The world frame is a fixed coordinate system (e.g., 'map' or 'odom').
    This is necessary because the robot's motors are controlled by commands in its own frame
    (e.g., "move forward at 0.5 m/s"), not the world frame (e.g., "move north at 0.5 m/s").
    """
    # We use the negative yaw because we are rotating the vector from world -> body.
    # This is equivalent to rotating the coordinate system by +yaw.
    c, s = math.cos(-yaw), math.sin(-yaw)
    # This is a standard 2D rotation matrix multiplication:
    # [ vx_b ] = [ cos(-yaw)  -sin(-yaw) ] [ vx_w ]
    # [ vy_b ]   [ sin(-yaw)   cos(-yaw) ] [ vy_w ]
    return c * vx_w - s * vy_w, s * vx_w + c * vy_w

    # ---
    # SUGGESTED IMPROVEMENT:
    # What would the inverse function, `rotate_body_to_world`, look like?
    # Think about what angle you would use in the cos() and sin() functions.
    # ---

def apply_tf_to_point(t: TransformStamped, px: float, py: float, pz: float) -> tuple[float, float, float]:
    """
    Apply a TransformStamped (translation + rotation) to a point (px, py, pz).
    This function manually performs the math to transform a point from one frame to another.
    The final point is the rotated point plus the translation.
    """
    # Extract the translation components from the transform message.
    tx, ty, tz = t.transform.translation.x, t.transform.translation.y, t.transform.translation.z
    # Extract the rotation components (as a quaternion).
    qx, qy, qz, qw = t.transform.rotation.x, t.transform.rotation.y, t.transform.rotation.z, t.transform.rotation.w

    # Manually compute the elements of the 3x3 rotation matrix from the quaternion.
    # This is a standard conversion formula.
    xx = qx*qx; yy = qy*qy; zz = qz*qz
    xy = qx*qy; xz = qx*qz; yz = qy*qz
    wx = qw*qx; wy = qw*qy; wz = qw*qz
    r00 = 1.0 - 2.0*(yy + zz); r01 = 2.0*(xy - wz);     r02 = 2.0*(xz + wy)
    r10 = 2.0*(xy + wz);     r11 = 1.0 - 2.0*(xx + zz); r12 = 2.0*(yz - wx)
    r20 = 2.0*(xz - wy);     r21 = 2.0*(yz + wx);       r22 = 1.0 - 2.0*(xx + yy)

    # Apply the rotation to the point (matrix-vector multiplication).
    rx = r00*px + r01*py + r02*pz
    ry = r10*px + r11*py + r12*pz
    rz = r20*px + r21*py + r22*pz
    
    # Add the translation to the rotated point.
    return rx + tx, ry + ty, rz + tz

    # ---
    # SUGGESTED IMPROVEMENT:
    # This manual math is great for understanding but can be complex.
    # ROS provides libraries to simplify this. For example, you could use the
    # `tf2_geometry_msgs` package which provides a `do_transform_point` function.
    # Try replacing the logic in `_on_goal` that uses this function with the library version.
    # ---


# ========= PID CONTROLLER CLASS =========
# A simple implementation of a PID (Proportional-Integral-Derivative) controller.

class PID:
    def __init__(self, kp=0.0, ki=0.0, kd=0.0):
        """
        Constructor for the PID controller. Initializes gains and state variables.
        """
        # The PID gains determine the controller's behavior.
        self.kp = kp  # Proportional gain: reacts to the current error.
        self.ki = ki  # Integral gain: corrects for steady-state error over time.
        self.kd = kd  # Derivative gain: dampens oscillations by reacting to the rate of change of the error.

        # State variables for the controller.
        self.i = 0.0  # Accumulator for the integral term.
        self.prev_e: Optional[float] = None  # Stores the previous error to calculate the derivative.

    def reset(self) -> None:
        """
        Resets the controller's state.
        This should be called when a new goal is set to clear out old integral and derivative data.
        """
        self.i = 0.0
        self.prev_e = None

    def step(self, e: float, dt: float) -> float:
        """
        Calculate one step of the PID output.
        - e: The current error (target - actual).
        - dt: The time elapsed since the last step (delta time).
        Returns the control output.
        """
        # A safety check to ignore invalid time steps, which can happen at startup or during simulation glitches.
        if dt <= 0.0 or dt > 0.5:
            dt = 0.0
        
        # Integral term (I): Accumulate the error over time.
        # This helps eliminate small, persistent errors.
        self.i += e * dt

        # ---
        # SUGGESTED IMPROVEMENT: Implement "integral windup" protection.
        # If the robot is stuck, the integral term 'self.i' can grow very large,
        # causing a huge overshoot when the robot finally moves.
        # Add logic to clamp 'self.i' to a reasonable range, e.g., `self.i = max(-1.0, min(1.0, self.i))`.
        # ---

        # Derivative term (D): Calculate the rate of change of the error.
        # This helps to slow down as the robot approaches the target, reducing overshoot.
        # If there's no previous error or no time has passed, the derivative is zero.
        d = 0.0 if (self.prev_e is None or dt == 0.0) else (e - self.prev_e) / dt
        
        # Store the current error for the next iteration.
        self.prev_e = e

        # The final PID output is the sum of the three terms.
        return self.kp * e + self.ki * self.i + self.kd * d

# ========= MAIN ROS 2 NODE CLASS =========

class Goal3DController(Node):
    def __init__(self) -> None:
        """
        Constructor for the main ROS 2 Node.
        This is where we set up parameters, publishers, subscribers, etc.
        """
        super().__init__("goal_3d_controller")

        # --- Hardcoded Topics & Frames for this lab ---
        # In a more general node, these would be parameters. For this lab, we fix them.
        self.goal_topic = "/goal_pose"
        self.cmd_vel_topic = "/crazyflie/cmd_vel"
        self.target_frame = "map"
        self.base_frame = "crazyflie/base_footprint"
        self.odom_topic = "/crazyflie/odom"

        # --- Parameters ---
        # Declare parameters that can be configured from the command line or a launch file.
        # This makes the node flexible and reusable.

        # Odometry → TF bridge (optional but ON by default for student simplicity)
        # This feature reads odometry messages and publishes them as TF transforms.
        # This is useful if another node provides odometry but not TF.
        self.declare_parameter("bridge_odom_tf", True)
        self.declare_parameter("connect_target_to_odom", True)  # Creates a static link: target_frame -> odom_frame

        # Control loop
        self.declare_parameter("control_rate_hz", 30.0) # Frequency of the main control loop.

        # Gains (default 0 → students must tune)
        # We loop to create parameters for each axis (x, y, z) and each gain (kp, ki, kd).
        for ax in ("x", "y", "z"):
            self.declare_parameter(f"kp_{ax}", 0.0)
            self.declare_parameter(f"ki_{ax}", 0.0)
            self.declare_parameter(f"kd_{ax}", 0.0)

        # Velocity limits
        # These are safety limits to prevent the robot from moving too fast.
        self.declare_parameter("max_v_x", 1.0)
        self.declare_parameter("max_v_y", 1.0)
        self.declare_parameter("max_v_z", 1.0)
        self.declare_parameter("max_w_z", 1.0)  # unused (yaw disabled)

        # Tolerances for "reached" (meters)
        # If the robot is within this distance of the goal, it will stop.
        self.declare_parameter("tol_xy_m", 0.03)
        self.declare_parameter("tol_z_m", 0.03)

        # --- Resolve (get) params ---
        # Retrieve the values of the parameters we just declared.
        self.bridge_odom_tf = bool(self.get_parameter("bridge_odom_tf").value)
        self.connect_target_to_odom = bool(self.get_parameter("connect_target_to_odom").value)

        rate_hz = float(self.get_parameter("control_rate_hz").value)
        self.dt = 1.0 / max(rate_hz, 1.0) # Calculate the time step 'dt' from the rate.

        # Get PID gains from parameters.
        self.kp_x = float(self.get_parameter("kp_x").value)
        self.ki_x = float(self.get_parameter("ki_x").value)
        self.kd_x = float(self.get_parameter("kd_x").value)
        self.kp_y = float(self.get_parameter("kp_y").value)
        self.ki_y = float(self.get_parameter("ki_y").value)
        self.kd_y = float(self.get_parameter("kd_y").value)
        self.kp_z = float(self.get_parameter("kp_z").value)
        self.ki_z = float(self.get_parameter("ki_z").value)
        self.kd_z = float(self.get_parameter("kd_z").value)

        # Get velocity limits from parameters.
        self.max_v_x = float(self.get_parameter("max_v_x").value)
        self.max_v_y = float(self.get_parameter("max_v_y").value)
        self.max_v_z = float(self.get_parameter("max_v_z").value)
        self.max_w_z = float(self.get_parameter("max_w_z").value)

        # Get tolerances from parameters.
        self.tol_xy = float(self.get_parameter("tol_xy_m").value)
        self.tol_z = float(self.get_parameter("tol_z_m").value)

        # --- ROS I/O (Input/Output) ---
        # Create a publisher to send Twist commands (velocity).
        self.pub_cmd = self.create_publisher(Twist, self.cmd_vel_topic, 10)
        # Create a subscriber to receive PoseStamped goals. When a message arrives, the `_on_goal` method is called.
        self.sub_goal = self.create_subscription(PoseStamped, self.goal_topic, self._on_goal, 10)

        # --- TF infrastructure ---
        self.tf_buffer = Buffer() # Caches TF data.
        self.tf_listener = TransformListener(self.tf_buffer, self) # Listens for TF messages.
        self.br = TransformBroadcaster(self) # Publishes dynamic (changing) transforms.
        self.sbr = StaticTransformBroadcaster(self) # Publishes static (non-changing) transforms.
        self._static_connected = False  # A flag to ensure we only publish the static transform once.

        # --- PID controller instances ---
        # Create three separate PID controllers, one for each axis, using the gains from parameters.
        self.pid_x = PID(self.kp_x, self.ki_x, self.kd_x)
        self.pid_y = PID(self.kp_y, self.ki_y, self.kd_y)
        self.pid_z = PID(self.kp_z, self.ki_z, self.kd_z)

        # --- State variables ---
        self.goal_in_target: Optional[PoseStamped] = None # Stores the current goal. 'None' means no goal is active.
        self.last_time = self.get_clock().now() # Used to calculate 'dt' in the control loop.

        # --- Optional: bridge odom → TF ---
        if self.bridge_odom_tf:
            # If the bridge is enabled, subscribe to the odometry topic.
            self.create_subscription(Odometry, self.odom_topic, self._odom_cb, 10)
            self.get_logger().info(f"TF bridge ON: listening to {self.odom_topic} to publish odom->base TF.")

        # --- Control timer ---
        # This timer will call the `_control_step` function at the specified frequency (e.g., 30 Hz).
        # This is the main loop of our controller.
        self.create_timer(self.dt, self._control_step)

        self.get_logger().info(
            f"goal_3d_controller up. gains default to 0.0 (you must tune). "
            f"goal='{self.goal_topic}', cmd='{self.cmd_vel_topic}', target='{self.target_frame}', base='{self.base_frame}'"
        )

    # -------- Subscription Callbacks --------
    
    def _on_goal(self, msg: PoseStamped) -> None:
        """
        Callback function that is executed whenever a new goal is received.
        """
        # The robot's pose is in 'target_frame'. The goal must also be in 'target_frame' for the math to be correct.
        # This code checks if the incoming goal message is in a different frame.
        if msg.header.frame_id and msg.header.frame_id != self.target_frame:
            try:
                # Use the TF buffer to look up the transformation from the goal's frame to our target frame.
                tf = self.tf_buffer.lookup_transform(
                    target_frame=self.target_frame,
                    source_frame=msg.header.frame_id,
                    time=Time(), # Get the latest available transform.
                    timeout=Duration(seconds=0.25),
                )
                # Use our helper function to apply the transform to the goal's position.
                gx, gy, gz = apply_tf_to_point(tf, msg.pose.position.x, msg.pose.position.y, msg.pose.position.z)
                
                # Create a new PoseStamped message to store the transformed goal.
                goal = PoseStamped()
                goal.header.stamp = self.get_clock().now().to_msg()
                goal.header.frame_id = self.target_frame # The frame is now our target frame.
                goal.pose.position.x = gx; goal.pose.position.y = gy; goal.pose.position.z = gz
                goal.pose.orientation = msg.pose.orientation  # Yaw is not used, so we just copy the orientation.

                # ---
                # SUGGESTED IMPROVEMENT:
                # For a controller that cares about yaw, you would need to transform the orientation as well.
                # The `tf2_geometry_msgs.do_transform_pose` function can transform both position and orientation.
                # ---

                # Store the new, transformed goal.
                self.goal_in_target = goal
                # Reset the PID controllers to start fresh for this new goal.
                self.pid_x.reset(); self.pid_y.reset(); self.pid_z.reset()
                self.get_logger().info(f"Goal received in '{msg.header.frame_id}', transformed to '{self.target_frame}'.")
            except Exception as e:
                # If the transform fails (e.g., TF doesn't know about the goal's frame), log a warning.
                self.get_logger().warn(f"Goal transform failed ({msg.header.frame_id} -> {self.target_frame}): {e}")
        else:
            # If the goal is already in the target frame, just store it.
            self.goal_in_target = msg
            # Reset the PID controllers.
            self.pid_x.reset(); self.pid_y.reset(); self.pid_z.reset()
            self.get_logger().info(f"Goal received in '{msg.header.frame_id or self.target_frame}'.")

    def _odom_cb(self, msg: Odometry) -> None:
        """
        Callback for the odom->TF bridge. Publishes a transform from the odometry message.
        """
        # --- Publish dynamic TF: odom_parent -> base_frame ---
        # Determine the parent and child frame IDs from the message or parameters.
        parent = msg.header.frame_id or "odom"
        child = msg.child_frame_id or self.base_frame

        # Create a TransformStamped message to publish.
        t = TransformStamped()
        # Use the timestamp from the odom message if available, otherwise use current time.
        t.header.stamp = msg.header.stamp if (msg.header.stamp.sec or msg.header.stamp.nanosec) else self.get_clock().now().to_msg()
        t.header.frame_id = parent
        t.child_frame_id = child
        # Copy the pose (translation and rotation) from the odometry message.
        t.transform.translation.x = msg.pose.pose.position.x
        t.transform.translation.y = msg.pose.pose.position.y
        t.transform.translation.z = msg.pose.pose.position.z
        t.transform.rotation = msg.pose.pose.orientation
        # Broadcast the transform to the /tf topic.
        self.br.sendTransform(t)

        # --- One-time static identity to connect target_frame → odom_parent ---
        # This is a common setup: `map` -> `odom` -> `base_link`.
        # The `map`->`odom` transform is often static (or published by a localization system).
        # Here, we publish a static identity transform (no change) to link them.
        if self.connect_target_to_odom and not self._static_connected:
            st = TransformStamped()
            st.header.stamp = t.header.stamp
            st.header.frame_id = self.target_frame # e.g., 'map'
            st.child_frame_id = parent # e.g., 'odom'
            # The transform is an identity: zero translation, and a quaternion representing no rotation.
            st.transform.translation.x = 0.0
            st.transform.translation.y = 0.0
            st.transform.translation.z = 0.0
            st.transform.rotation.x = 0.0
            st.transform.rotation.y = 0.0
            st.transform.rotation.z = 0.0
            st.transform.rotation.w = 1.0
            # Publish using the static transform broadcaster.
            self.sbr.sendTransform(st)
            self._static_connected = True # Set flag so we don't publish again.
            self.get_logger().info(f"Connected {self.target_frame} -> {parent} (static identity).")

            # ---
            # SUGGESTED IMPROVEMENT:
            # Publishing a static transform from code is convenient, but it's often better practice
            # to define static transforms in a ROS 2 Launch File using the `static_transform_publisher` node.
            # This separates configuration from code.
            # ---

    # -------- Control loop --------
    def _control_step(self) -> None:
        """
        This is the main control loop, called periodically by the timer.
        """
        # If we don't have a goal, there's nothing to do.
        if self.goal_in_target is None:
            return

        # Calculate delta time (dt) since the last loop iteration.
        now = self.get_clock().now()
        dt = (now - self.last_time).nanoseconds / 1e9
        self.last_time = now
        # Fallback to the nominal dt if the calculated one is strange.
        if dt <= 0.0 or dt > 0.5:
            dt = self.dt

        # --- Get the robot's current pose in the target frame using TF ---
        try:
            # This is the core TF lookup. We ask for the transform from the robot's base to the world frame.
            tf = self.tf_buffer.lookup_transform(
                target_frame=self.target_frame,
                source_frame=self.base_frame,
                time=Time(), # Latest available
                timeout=Duration(seconds=0.1),
            )
        except Exception as e:
            # If TF lookup fails, we don't know where the robot is.
            # For safety, command the robot to hover in place (all velocities zero).
            self._publish_cmd(0.0, 0.0, 0.0, 0.0)
            # Log a throttled warning so we don't spam the console.
            self.get_logger().warn("TF lookup failed (target <- base). Hovering.", throttle_duration_sec=2.0)
            return

        # --- Extract current state from the transform ---
        x = tf.transform.translation.x
        y = tf.transform.translation.y
        z = tf.transform.translation.z
        q = tf.transform.rotation
        yaw = quat_to_yaw(q.x, q.y, q.z, q.w)

        # --- Get goal position ---
        gx = self.goal_in_target.pose.position.x
        gy = self.goal_in_target.pose.position.y
        gz = self.goal_in_target.pose.position.z

        # --- Calculate error (Goal - Current) ---
        ex = gx - x
        ey = gy - y
        ez = gz - z

        # --- Run PID controllers ---
        # The PID controllers compute the desired velocity in the WORLD frame based on the error.
        ux_w = self.pid_x.step(ex, dt)
        uy_w = self.pid_y.step(ey, dt)
        uz_w = self.pid_z.step(ez, dt)

        # --- Rotate control output into the robot's BODY frame ---
        # The robot understands commands like "move forward", not "move north".
        ux_b, uy_b = rotate_world_to_body(ux_w, uy_w, yaw)
        wz_b = 0.0  # Yaw control is explicitly disabled for this lab.

        # --- Saturate (clamp) the outputs to the maximum velocity limits ---
        # This prevents the controller from demanding impossibly high speeds.
        ux_b = max(-self.max_v_x, min(self.max_v_x, ux_b))
        uy_b = max(-self.max_v_y, min(self.max_v_y, uy_b))
        uz_b = max(-self.max_v_z, min(self.max_v_z, uz_w))
        wz_b = max(-self.max_w_z, min(self.max_w_z, wz_b))

        # --- Apply a deadband: stop when very close to the goal ---
        # This prevents the robot from jittering or oscillating when it's "close enough".
        if abs(ex) < self.tol_xy and abs(ey) < self.tol_xy and abs(ez) < self.tol_z:
            ux_b = 0.0; uy_b = 0.0; uz_b = 0.0
        
            # ---
            # SUGGESTED IMPROVEMENT:
            # This deadband is simple. A more robust system might also check if the robot's
            # velocity is low before stopping. You could also add a log message here like:
            # self.get_logger().info("Goal reached!", once=True)
            # The `once=True` argument would prevent the message from spamming the console.
            # ---

        # Publish the final command.
        self._publish_cmd(ux_b, uy_b, uz_b, wz_b)

    def _publish_cmd(self, vx: float, vy: float, vz: float, wz: float) -> None:
        """
        Helper function to construct and publish a Twist message.
        """
        # Create a new Twist message.
        msg = Twist()
        # Assign the linear velocities (body frame).
        msg.linear.x = vx
        msg.linear.y = vy
        msg.linear.z = vz
        # Assign the angular velocity (body frame).
        msg.angular.z = wz  # yaw is disabled in this lab, so this will be 0.
        # Publish the message.
        self.pub_cmd.publish(msg)

def main(args=None) -> None:
    """
    The main function that sets up and runs the ROS 2 node.
    """
    # Initialize the rclpy library.
    rclpy.init(args=args)
    # Create an instance of our controller node.
    node = Goal3DController()
    try:
        # `spin` keeps the node alive and processing callbacks (like from timers and subscriptions).
        # It will block here until the node is shut down (e.g., by Ctrl+C).
        rclpy.spin(node)
    except KeyboardInterrupt:
        # This block catches the Ctrl+C signal to allow for a graceful shutdown.
        pass
    finally:
        # Cleanly destroy the node and shut down rclpy.
        node.destroy_node()
        rclpy.shutdown()

# This is a standard Python entry point.
# If this script is executed directly, the `main` function will be called.
if __name__ == "__main__":
    main()