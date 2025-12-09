# Velocity-Controlled Single Joint Motion Guide

## Kinova Gen3 Lite with ROS2 Jazzy

This guide covers how to move a single joint at a specified angular velocity—a fundamentally different control objective than standard motion planning.

---

## 1. Understanding the Problem

### What MoveIt2 Does Well

MoveIt2 excels at **point-to-point motion planning**:

- "Move the end effector to position (x, y, z)"
- "Move to this joint configuration"
- "Follow this Cartesian path while avoiding obstacles"

The planner finds a collision-free path and generates a time-optimal trajectory. You specify *where* to go; MoveIt decides *how fast* to get there.

### What We Need Instead

Some applications require direct control over joint velocity rather than end position:

- Move **one specific joint** at a **controlled velocity**
- Other joints should remain **stationary**
- The velocity profile matters more than reaching a specific end position

Examples include pendulum motions, swing mechanics, constant-speed scanning, velocity characterization experiments, and any application where the *rate* of motion is the controlled variable.

This is **velocity control**, not **position control**.

### Why Standard MoveIt Planning Won't Work

Consider what happens if you try:

```python
# This won't give you velocity control
moveit2.move_to_configuration([0, 0, 1.57, 0, 0, 0])  # Move joint_3 to 90°
```

MoveIt will:
1. Plan a path from current position to goal
2. Time-parameterize it for smoothness and speed limits
3. Potentially move other joints to optimize the path
4. Use its own velocity profile (typically trapezoidal)

You have no direct control over the angular velocity during the motion.

---

## 2. The Solution: Direct Trajectory Publishing

### Architecture Overview

The Kinova Gen3 Lite uses `ros2_control` with a `joint_trajectory_controller`. This controller accepts `JointTrajectory` messages and interpolates between waypoints.

```
┌─────────────────────┐
│   Your Python Node  │
└──────────┬──────────┘
           │ JointTrajectory msg
           ▼
┌─────────────────────────────────────────┐
│  /joint_trajectory_controller/          │
│           joint_trajectory              │
└──────────┬──────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│   joint_trajectory_controller           │
│   (interpolates between waypoints)      │
└──────────┬──────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│   Hardware Interface / Robot            │
└─────────────────────────────────────────┘
```

**Key insight**: You can publish directly to this topic, bypassing MoveIt entirely.

### The Relevant ROS2 Topic

```bash
# The topic you'll publish to:
/joint_trajectory_controller/joint_trajectory

# Message type:
trajectory_msgs/msg/JointTrajectory
```

---

## 3. Understanding JointTrajectory Messages

### Message Structure

```
trajectory_msgs/msg/JointTrajectory:
    std_msgs/Header header
    string[] joint_names
    JointTrajectoryPoint[] points

trajectory_msgs/msg/JointTrajectoryPoint:
    float64[] positions
    float64[] velocities      # Optional but recommended
    float64[] accelerations   # Optional
    float64[] effort          # Optional
    builtin_interfaces/Duration time_from_start
```

### What Each Field Means

| Field | Purpose |
|-------|---------|
| `joint_names` | Which joints this trajectory controls (order matters!) |
| `points` | Sequence of waypoints the robot passes through |
| `positions` | Target joint angles at this waypoint (radians) |
| `velocities` | Target joint velocities at this waypoint (rad/s) |
| `time_from_start` | When to reach this waypoint (relative to trajectory start) |

### The Key Relationship

**Velocity is determined by the relationship between position and time:**

$$\omega = \frac{\Delta\theta}{\Delta t}$$

If you want joint 3 to move at 30°/s through a 90° arc:

$$t = \frac{90°}{30°/s} = 3.0 \text{ seconds}$$

By carefully choosing `positions` and `time_from_start` for each waypoint, you control the velocity.

---

## 4. Velocity Control Through Time-Parameterization

### Constant Velocity Motion

For constant velocity, use **linear interpolation** between waypoints:

```
Position
    │
    │         ╱
    │       ╱
    │     ╱      ← Constant slope = constant velocity
    │   ╱
    │ ╱
    └──────────────── Time
```

If you space waypoints with equal position increments and equal time increments, the velocity between them is constant.

### Example Calculation

**Goal**: Move joint_3 from 0° to 45° at 30°/s

**Step 1**: Calculate total time
```
total_time = |45° - 0°| / 30°/s = 1.5 seconds
```

**Step 2**: Create waypoints (e.g., 10 waypoints)
```
For i = 0 to 10:
    alpha = i / 10                           # 0.0, 0.1, 0.2, ... 1.0
    position = start + alpha * total_angle   # Linear interpolation
    time = alpha * total_time                # Linear time spacing
```

**Step 3**: All other joints stay at their current positions

### Trapezoidal Velocity Profile

Real systems can't achieve instant velocity changes. A trapezoidal profile is more realistic:

```
Velocity
    │     ┌─────────┐
    │    ╱           ╲
    │   ╱             ╲
    │  ╱               ╲
    │ ╱                 ╲
    └──────────────────────── Time
      Accel  Cruise  Decel
```

This requires more complex position calculations:

- **Acceleration phase**: Position follows quadratic curve
- **Cruise phase**: Position follows linear curve  
- **Deceleration phase**: Position follows quadratic curve

**Think carefully about**: How do you calculate position as a function of time for each phase? What kinematic equations apply?

---

## 5. Implementation Approach

### Step 1: Get Current Joint States

Before commanding motion, you need to know where the robot currently is.

**Subscribe to**: `/joint_states` (type: `sensor_msgs/msg/JointState`)

```python
from sensor_msgs.msg import JointState

# The callback receives messages like:
# JointState:
#   name: ['joint_1', 'joint_2', 'joint_3', 'joint_4', 'joint_5', 'joint_6', ...]
#   position: [0.1, -0.5, 1.2, 0.0, -0.3, 0.0, ...]
#   velocity: [...]
#   effort: [...]
```

**Note**: The gripper joint is also included in `/joint_states`. You need to extract only the arm joints.

### Step 2: Build the Trajectory Message

```python
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration

trajectory = JointTrajectory()
trajectory.joint_names = ["joint_1", "joint_2", "joint_3", "joint_4", "joint_5", "joint_6"]

# For each waypoint...
point = JointTrajectoryPoint()
point.positions = [...]  # All 6 joint positions
point.velocities = [...]  # Optional: helps controller
point.time_from_start = Duration(sec=..., nanosec=...)

trajectory.points.append(point)
```

### Step 3: Publish the Trajectory

```python
from trajectory_msgs.msg import JointTrajectory

publisher = node.create_publisher(
    JointTrajectory,
    '/joint_trajectory_controller/joint_trajectory',
    10
)

publisher.publish(trajectory)
```

### Step 4: Wait for Completion

The trajectory executes asynchronously. You can either:

1. **Simple approach**: `time.sleep(total_trajectory_time + buffer)`
2. **Better approach**: Monitor `/joint_trajectory_controller/state` for completion

---

## 6. Keeping Other Joints Stationary

This is critical for single-joint motion. Every `JointTrajectoryPoint` must specify positions for **all joints** in `joint_names`.

```python
# Current positions from /joint_states
current = [0.1, -0.5, 1.2, 0.0, -0.3, 0.0]

# For each waypoint, copy current positions and modify only the target joint
positions = list(current)  # Make a copy!
positions[2] = new_joint_3_position  # Only change joint_3 (index 2)

point.positions = positions
```

**Common mistake**: Only specifying the moving joint. The controller needs all joint positions.

---

## 7. Gen3 Lite Specifics

### Joint Configuration

| Index | Name | Type | Notes |
|-------|------|------|-------|
| 0 | joint_1 | Continuous | Base rotation |
| 1 | joint_2 | Revolute | Shoulder (limits: ±2.41 rad) |
| 2 | joint_3 | Continuous | Elbow - no joint limits |
| 3 | joint_4 | Revolute | Wrist 1 (limits: ±2.66 rad) |
| 4 | joint_5 | Continuous | Wrist 2 |
| 5 | joint_6 | Revolute | Wrist 3 (limits: ±2.23 rad) |

**Joint 3 (elbow)** is continuous (no joint limits), making it suitable for large-range motions without worrying about limit violations.

### Recommended Velocity Limits

While the robot has maximum velocity limits, for initial testing use conservative values:

- **Testing**: 15-30 °/s (0.26-0.52 rad/s)
- **Moderate**: 30-60 °/s (0.52-1.05 rad/s)
- **Fast** (use caution): 60-90 °/s (1.05-1.57 rad/s)

### Launch Requirements

Your node should run **after** the robot bringup:

```bash
# Terminal 1: Launch robot with MoveIt
ros2 launch kinova_gen3_lite_moveit_config robot.launch.py \
    robot_ip:=192.168.1.10

# Terminal 2: Run your velocity control node
ros2 run your_package your_node
```

---

## 8. Debugging Tips

### Verify Joint States are Received

```bash
ros2 topic echo /joint_states --once
```

### Check Controller is Active

```bash
ros2 control list_controllers
# Should show: joint_trajectory_controller [active]
```

### Test with Command Line First

Before writing code, test direct publishing:

```bash
ros2 topic pub /joint_trajectory_controller/joint_trajectory \
    trajectory_msgs/msg/JointTrajectory "{
        joint_names: [joint_1, joint_2, joint_3, joint_4, joint_5, joint_6],
        points: [
            {positions: [0, 0, 0, 0, 0, 0], time_from_start: {sec: 0}},
            {positions: [0, 0, 0.5, 0, 0, 0], time_from_start: {sec: 2}}
        ]
    }" --once
```

### Monitor Trajectory Execution

```bash
ros2 topic echo /joint_trajectory_controller/state
```

---

## 9. Design Questions to Consider

Before implementing, think through these questions:

1. **How many waypoints do you need?** More waypoints = smoother motion, but diminishing returns. What's a reasonable number?

2. **What happens at the start and end?** Should velocity be zero at endpoints, or can it be non-zero?

3. **How do you handle the Duration message?** It has `sec` (int) and `nanosec` (int) fields. How do you convert a float time to this format?

4. **What if the robot is already moving?** Should you check the current state before commanding?

5. **What's a safe motion range for testing?** Start small (e.g., 15-30°) before attempting larger motions.

6. **Should you include velocity fields in waypoints?** The controller can interpolate without them, but including them may improve tracking.

---

## 10. Code Structure Suggestion

```python
#!/usr/bin/env python3
"""Velocity-controlled single joint motion."""

import rclpy
from rclpy.node import Node
# ... other imports ...

class SingleJointVelocityController(Node):
    def __init__(self):
        super().__init__('single_joint_velocity_controller')
        
        # TODO: Create subscriber for /joint_states
        # TODO: Create publisher for /joint_trajectory_controller/joint_trajectory
        # TODO: Store current joint positions when received
    
    def joint_state_callback(self, msg):
        # TODO: Extract arm joint positions from message
        # Hint: msg.name and msg.position are parallel arrays
        pass
    
    def move_joint_at_velocity(self, joint_index, angular_velocity, total_angle):
        """
        Command a single joint to move at specified velocity.
        
        Args:
            joint_index: Which joint (0-5)
            angular_velocity: Desired speed in rad/s
            total_angle: How far to move in radians
        """
        # TODO: Calculate total time from velocity and angle
        # TODO: Generate waypoints with appropriate time spacing
        # TODO: Build JointTrajectory message
        # TODO: Publish trajectory
        pass

def main():
    rclpy.init()
    node = SingleJointVelocityController()
    # ... spin and execute ...
    rclpy.shutdown()
```

---

## 11. Extension Challenges

Once basic velocity control works:

1. **Trapezoidal profile**: Implement smooth acceleration and deceleration phases

2. **Bidirectional motion**: Move forward, then reverse (oscillating behavior)

3. **Velocity feedback**: Monitor actual velocity during motion and compare to commanded

4. **Multiple joints**: What if you wanted two joints to move at related velocities?

5. **Safety limits**: Add checks for joint limits, maximum velocities, and collision avoidance

---

## References

- `trajectory_msgs/msg/JointTrajectory` - [ROS2 Documentation](https://docs.ros.org/en/jazzy/p/trajectory_msgs/)
- `ros2_control` - [GitHub](https://github.com/ros-controls/ros2_control)
- Your lab's `pymoveit2_api_guide.md` - For understanding the MoveIt2 interface you're *not* using here
- Your lab's `kinova_gen3_lite_moveit2_guide.md` - For robot-specific configuration details

---

*This guide is intended for educational purposes in the Duke Robotics Lab. The concepts apply broadly to any robot using ros2_control with a joint_trajectory_controller.*
