# Kinova Gen3 Lite with MoveIt2 Python API Guide

A comprehensive guide for using the Kinova Gen3 Lite robot arm with the MoveIt2 Python API in ROS2 Jazzy using the `ros2_kortex` package.

---

## Table of Contents

1. [Gen3 Lite Overview](#gen3-lite-overview)
2. [Installation & Setup](#installation--setup)
3. [Robot Configuration Reference](#robot-configuration-reference)
4. [Launching the Robot](#launching-the-robot)
5. [Using MoveIt2 Python API with Gen3 Lite](#using-moveit2-python-api-with-gen3-lite)
6. [Gripper Control](#gripper-control)
7. [Complete Examples](#complete-examples)
8. [Real-Time Servo Control](#real-time-servo-control)
9. [Common Operations](#common-operations)
10. [Troubleshooting](#troubleshooting)

---

## Gen3 Lite Overview

The Kinova Gen3 Lite is a compact, ultra-lightweight 6-DOF robotic arm designed for education and light manipulation tasks.

### Specifications

| Property | Value |
|----------|-------|
| Degrees of Freedom | 6 |
| Payload | 0.5 kg |
| Reach | 760 mm |
| Weight | 5.2 kg |
| Gripper | Integrated 2-finger gripper (gen3_lite_2f) |
| Default IP Address | 192.168.1.10 |
| Communication | USB (RNDIS) or Ethernet |

### Kinematic Chain

```
base_link
    └── shoulder_link (joint_1: revolute)
        └── half_arm_1_link (joint_2: revolute)
            └── half_arm_2_link (joint_3: revolute)
                └── forearm_link (joint_4: revolute)
                    └── spherical_wrist_1_link (joint_5: revolute)
                        └── spherical_wrist_2_link (joint_6: revolute)
                            └── bracelet_link
                                └── end_effector_link
                                    └── tool_frame
                                        └── gripper_base_link
                                            ├── right_finger_prox_link
                                            │   └── right_finger_dist_link
                                            └── left_finger_prox_link
                                                └── left_finger_dist_link
```

---

## Installation & Setup

### Prerequisites

- Ubuntu 24.04
- ROS2 Jazzy
- MoveIt2 (recommended: install from binary)
- Cyclone DDS (recommended for MoveIt)

### 1. Install ROS2 Jazzy

Follow the official installation guide: https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html

### 2. Install Cyclone DDS (Recommended for MoveIt)

```bash
sudo apt install ros-jazzy-rmw-cyclonedds-cpp
echo 'export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp' >> ~/.bashrc
source ~/.bashrc
```

### 3. Create Workspace and Clone ros2_kortex

```bash
# Install build tools
sudo apt install python3-colcon-common-extensions python3-vcstool

# Create workspace
export COLCON_WS=~/ros2_kortex_ws
mkdir -p $COLCON_WS/src
cd $COLCON_WS

# Clone ros2_kortex
git clone https://github.com/Kinovarobotics/ros2_kortex.git src/ros2_kortex

# Import dependencies
vcs import src --skip-existing --input src/ros2_kortex/ros2_kortex.jazzy.repos
vcs import src --skip-existing --input src/ros2_kortex/ros2_kortex-not-released.jazzy.repos

# For Gazebo simulation (optional)
vcs import src --skip-existing --input src/ros2_kortex/simulation.jazzy.repos
```

### 4. Install Dependencies and Build

```bash
cd $COLCON_WS

# Install ROS dependencies
rosdep install --ignore-src --from-paths src -y -r

# Build (limit threads to avoid system freeze)
colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release --parallel-workers 3

# Source the workspace
echo "source $COLCON_WS/install/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

### 5. Network Configuration

The Gen3 Lite has a fixed IP address of `192.168.1.10`. Configure your network interface:

**For direct Ethernet connection:**
```bash
# Set your ethernet interface to the same subnet
sudo ip addr add 192.168.1.1/24 dev eth0
```

**For USB connection (RNDIS):**
The robot creates a virtual network interface. Configure it similarly.

---

## Robot Configuration Reference

### Joint Names

```python
# Gen3 Lite arm joints (6 DOF)
ARM_JOINT_NAMES = [
    "joint_1",  # Base rotation
    "joint_2",  # Shoulder
    "joint_3",  # Elbow
    "joint_4",  # Wrist 1
    "joint_5",  # Wrist 2
    "joint_6",  # Wrist 3 (end effector rotation)
]

# Gen3 Lite gripper joint
GRIPPER_JOINT_NAME = "right_finger_bottom_joint"
```

### Link Names

```python
BASE_LINK = "base_link"
END_EFFECTOR_LINK = "end_effector_link"  # Before gripper
TOOL_FRAME = "tool_frame"                 # After gripper mount
```

### Planning Groups

```python
ARM_GROUP_NAME = "manipulator"  # or "arm" depending on MoveIt config
GRIPPER_GROUP_NAME = "gripper"
```

### Joint Limits

| Joint | Lower Limit (rad) | Upper Limit (rad) |
|-------|-------------------|-------------------|
| joint_1 | -∞ (continuous) | +∞ |
| joint_2 | -2.41 | 2.41 |
| joint_3 | -∞ (continuous) | +∞ |
| joint_4 | -2.66 | 2.66 |
| joint_5 | -∞ (continuous) | +∞ |
| joint_6 | -2.23 | 2.23 |

### Gripper Positions

```python
GRIPPER_OPEN_POSITION = 0.0    # Fully open
GRIPPER_CLOSED_POSITION = 0.8  # Fully closed
```

---

## Launching the Robot

### Physical Robot

```bash
# Basic launch
ros2 launch kortex_bringup gen3_lite.launch.py \
    robot_ip:=192.168.1.10

# With specific options
ros2 launch kortex_bringup gen3_lite.launch.py \
    robot_ip:=192.168.1.10 \
    launch_rviz:=true \
    gripper:=gen3_lite_2f
```

### Simulation (Mock Hardware)

```bash
ros2 launch kortex_bringup gen3_lite.launch.py \
    robot_ip:=xxx.xxx.xxx.xxx \
    use_fake_hardware:=true
```

### MoveIt with Physical Robot

```bash
ros2 launch kinova_gen3_lite_moveit_config robot.launch.py \
    robot_ip:=192.168.1.10
```

### MoveIt with Mock Hardware

```bash
ros2 launch kinova_gen3_lite_moveit_config robot.launch.py \
    robot_ip:=xxx.xxx.xxx.xxx \
    use_fake_hardware:=true
```

### Launch File Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `robot_ip` | (required) | Robot IP address |
| `robot_type` | `gen3_lite` | Robot model |
| `gripper` | `gen3_lite_2f` | Gripper type |
| `gripper_joint_name` | `right_finger_bottom_joint` | Gripper joint |
| `use_fake_hardware` | `false` | Use mock hardware |
| `launch_rviz` | `true` | Launch RViz |
| `robot_controller` | `joint_trajectory_controller` | Controller type |

---

## Using MoveIt2 Python API with Gen3 Lite

### Basic Setup

```python
import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
import threading

# Import MoveIt2 Python API
from pymoveit2 import MoveIt2, MoveIt2State

class Gen3LiteController:
    """Controller class for Kinova Gen3 Lite using MoveIt2 Python API."""
    
    # Gen3 Lite Configuration
    JOINT_NAMES = ["joint_1", "joint_2", "joint_3", "joint_4", "joint_5", "joint_6"]
    BASE_LINK = "base_link"
    END_EFFECTOR = "tool_frame"  # or "end_effector_link"
    GROUP_NAME = "manipulator"
    
    def __init__(self):
        # Initialize ROS2 node
        rclpy.init()
        self.node = Node("gen3_lite_controller")
        
        # Use ReentrantCallbackGroup for blocking calls
        self.callback_group = ReentrantCallbackGroup()
        
        # Create MoveIt2 interface
        self.moveit2 = MoveIt2(
            node=self.node,
            joint_names=self.JOINT_NAMES,
            base_link_name=self.BASE_LINK,
            end_effector_name=self.END_EFFECTOR,
            group_name=self.GROUP_NAME,
            callback_group=self.callback_group,
        )
        
        # Configure motion parameters
        self.moveit2.max_velocity = 0.5
        self.moveit2.max_acceleration = 0.5
        
        # Start executor in background thread
        self.executor = MultiThreadedExecutor()
        self.executor.add_node(self.node)
        self.executor_thread = threading.Thread(target=self.executor.spin, daemon=True)
        self.executor_thread.start()
        
        self.node.get_logger().info("Gen3 Lite controller initialized")
    
    def move_to_joint_positions(self, positions: list, wait: bool = True) -> bool:
        """Move arm to specified joint positions."""
        self.moveit2.move_to_configuration(joint_positions=positions)
        if wait:
            return self.moveit2.wait_until_executed()
        return True
    
    def move_to_pose(self, position: tuple, orientation: tuple, wait: bool = True) -> bool:
        """Move end effector to Cartesian pose."""
        self.moveit2.move_to_pose(
            position=position,
            quat_xyzw=orientation,
        )
        if wait:
            return self.moveit2.wait_until_executed()
        return True
    
    def get_current_pose(self):
        """Get current end effector pose."""
        return self.moveit2.compute_fk()
    
    def get_current_joints(self):
        """Get current joint positions."""
        return self.moveit2.joint_state
    
    def shutdown(self):
        """Cleanup resources."""
        self.executor.shutdown()
        self.node.destroy_node()
        rclpy.shutdown()


# Usage
if __name__ == "__main__":
    controller = Gen3LiteController()
    
    # Move to home position
    home_position = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    controller.move_to_joint_positions(home_position)
    
    # Move to a Cartesian pose
    controller.move_to_pose(
        position=(0.4, 0.0, 0.3),
        orientation=(0.0, 0.707, 0.0, 0.707),  # 90° pitch
    )
    
    controller.shutdown()
```

### Complete Node Example

```python
#!/usr/bin/env python3
"""
Gen3 Lite MoveIt2 Python API Example Node

Launch the robot first:
    ros2 launch kinova_gen3_lite_moveit_config robot.launch.py robot_ip:=192.168.1.10

Then run this script:
    ros2 run your_package gen3_lite_example.py
"""

import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
import threading
import math

from pymoveit2 import MoveIt2, MoveIt2State, GripperInterface


class Gen3LiteMoveIt2Node(Node):
    """ROS2 Node for controlling Gen3 Lite with MoveIt2 Python API."""
    
    # Robot Configuration
    ARM_JOINTS = ["joint_1", "joint_2", "joint_3", "joint_4", "joint_5", "joint_6"]
    GRIPPER_JOINTS = ["right_finger_bottom_joint"]
    BASE_LINK = "base_link"
    END_EFFECTOR = "tool_frame"
    ARM_GROUP = "manipulator"
    GRIPPER_GROUP = "gripper"
    
    # Gripper positions
    GRIPPER_OPEN = [0.0]
    GRIPPER_CLOSED = [0.8]
    
    # Predefined poses (joint positions in radians)
    POSES = {
        "home": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        "ready": [0.0, -0.35, 1.57, 0.0, -1.22, 0.0],
        "vertical": [0.0, 0.0, 3.14, 0.0, 0.0, 0.0],
        "retracted": [0.0, -0.26, 0.96, 0.0, -0.70, 0.0],
    }
    
    def __init__(self):
        super().__init__("gen3_lite_moveit2_node")
        
        # Callback group for async operations
        self.callback_group = ReentrantCallbackGroup()
        
        # Initialize MoveIt2 arm interface
        self.arm = MoveIt2(
            node=self,
            joint_names=self.ARM_JOINTS,
            base_link_name=self.BASE_LINK,
            end_effector_name=self.END_EFFECTOR,
            group_name=self.ARM_GROUP,
            callback_group=self.callback_group,
            ignore_new_calls_while_executing=True,
        )
        
        # Initialize gripper interface
        self.gripper = GripperInterface(
            node=self,
            gripper_joint_names=self.GRIPPER_JOINTS,
            open_gripper_joint_positions=self.GRIPPER_OPEN,
            closed_gripper_joint_positions=self.GRIPPER_CLOSED,
            gripper_group_name=self.GRIPPER_GROUP,
            callback_group=self.callback_group,
            gripper_command_action_name="/gen3_lite_2f_gripper_controller/gripper_cmd",
        )
        
        # Configure motion parameters
        self._configure_motion_parameters()
        
        self.get_logger().info("Gen3 Lite MoveIt2 node initialized")
    
    def _configure_motion_parameters(self):
        """Configure default motion parameters."""
        self.arm.max_velocity = 0.5          # 50% of max velocity
        self.arm.max_acceleration = 0.5      # 50% of max acceleration
        self.arm.num_planning_attempts = 10  # Planning attempts
        self.arm.allowed_planning_time = 2.0 # Planning timeout (seconds)
    
    # ==================== Arm Control ====================
    
    def move_to_named_pose(self, pose_name: str) -> bool:
        """Move to a predefined named pose."""
        if pose_name not in self.POSES:
            self.get_logger().error(f"Unknown pose: {pose_name}")
            return False
        
        self.get_logger().info(f"Moving to pose: {pose_name}")
        self.arm.move_to_configuration(joint_positions=self.POSES[pose_name])
        return self.arm.wait_until_executed()
    
    def move_to_joints(self, positions: list) -> bool:
        """Move to specified joint positions (radians)."""
        if len(positions) != 6:
            self.get_logger().error("Expected 6 joint positions")
            return False
        
        self.arm.move_to_configuration(joint_positions=positions)
        return self.arm.wait_until_executed()
    
    def move_to_cartesian(
        self,
        x: float, y: float, z: float,
        qx: float = 0.0, qy: float = 0.707, qz: float = 0.0, qw: float = 0.707,
        cartesian: bool = False,
    ) -> bool:
        """Move end effector to Cartesian pose."""
        self.get_logger().info(f"Moving to position: ({x}, {y}, {z})")
        self.arm.move_to_pose(
            position=(x, y, z),
            quat_xyzw=(qx, qy, qz, qw),
            cartesian=cartesian,
            cartesian_max_step=0.01 if cartesian else 0.0025,
        )
        return self.arm.wait_until_executed()
    
    def move_linear(self, x: float, y: float, z: float) -> bool:
        """Move linearly in Cartesian space (maintains orientation)."""
        current_pose = self.arm.compute_fk()
        if current_pose is None:
            self.get_logger().error("Failed to get current pose")
            return False
        
        # Keep current orientation
        quat = current_pose.pose.orientation
        
        self.arm.move_to_pose(
            position=(x, y, z),
            quat_xyzw=(quat.x, quat.y, quat.z, quat.w),
            cartesian=True,
            cartesian_max_step=0.005,
            cartesian_fraction_threshold=0.9,
        )
        return self.arm.wait_until_executed()
    
    def get_end_effector_pose(self):
        """Get current end effector pose."""
        return self.arm.compute_fk()
    
    def get_joint_positions(self) -> list:
        """Get current joint positions."""
        joint_state = self.arm.joint_state
        if joint_state is None:
            return None
        
        # Extract positions for arm joints only
        positions = []
        for joint_name in self.ARM_JOINTS:
            if joint_name in joint_state.name:
                idx = joint_state.name.index(joint_name)
                positions.append(joint_state.position[idx])
        return positions
    
    # ==================== Gripper Control ====================
    
    def open_gripper(self) -> bool:
        """Open the gripper."""
        self.get_logger().info("Opening gripper")
        self.gripper.open()
        return self.gripper.wait_until_executed()
    
    def close_gripper(self) -> bool:
        """Close the gripper."""
        self.get_logger().info("Closing gripper")
        self.gripper.close()
        return self.gripper.wait_until_executed()
    
    def set_gripper_position(self, position: float) -> bool:
        """Set gripper to specific position (0.0=open, 0.8=closed)."""
        self.gripper.move_to_position(position)
        return self.gripper.wait_until_executed()
    
    def is_gripper_open(self) -> bool:
        """Check if gripper is open."""
        return self.gripper.is_open
    
    # ==================== Collision Objects ====================
    
    def add_table(self, height: float = 0.0):
        """Add a table collision object."""
        self.arm.add_collision_box(
            id="table",
            size=(1.0, 1.0, 0.02),
            position=(0.0, 0.0, height - 0.01),
            quat_xyzw=(0.0, 0.0, 0.0, 1.0),
        )
        self.get_logger().info(f"Added table at height {height}")
    
    def add_box_obstacle(self, name: str, size: tuple, position: tuple):
        """Add a box obstacle to the planning scene."""
        self.arm.add_collision_box(
            id=name,
            size=size,
            position=position,
            quat_xyzw=(0.0, 0.0, 0.0, 1.0),
        )
        self.get_logger().info(f"Added obstacle: {name}")
    
    def remove_obstacle(self, name: str):
        """Remove a collision object."""
        self.arm.remove_collision_object(name)
        self.get_logger().info(f"Removed obstacle: {name}")
    
    def attach_object(self, object_id: str):
        """Attach object to end effector."""
        self.arm.attach_collision_object(
            id=object_id,
            link_name=self.END_EFFECTOR,
            touch_links=["right_finger_prox_link", "right_finger_dist_link",
                        "left_finger_prox_link", "left_finger_dist_link"],
        )
    
    def detach_object(self, object_id: str):
        """Detach object from end effector."""
        self.arm.detach_collision_object(object_id)
    
    # ==================== Utility ====================
    
    def is_executing(self) -> bool:
        """Check if robot is currently executing a motion."""
        return self.arm.query_state() != MoveIt2State.IDLE
    
    def cancel_motion(self):
        """Cancel current motion."""
        self.arm.cancel_execution()
    
    def compute_ik(self, position: tuple, orientation: tuple):
        """Compute inverse kinematics for a pose."""
        return self.arm.compute_ik(position=position, quat_xyzw=orientation)


def main():
    rclpy.init()
    
    node = Gen3LiteMoveIt2Node()
    
    # Create executor
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    
    # Spin in background
    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()
    
    try:
        # Wait for robot to be ready
        node.get_logger().info("Waiting for robot...")
        import time
        time.sleep(2.0)
        
        # Demo sequence
        node.get_logger().info("Starting demo sequence")
        
        # 1. Move to home position
        node.move_to_named_pose("home")
        
        # 2. Open gripper
        node.open_gripper()
        
        # 3. Move to ready position
        node.move_to_named_pose("ready")
        
        # 4. Move to a Cartesian pose
        node.move_to_cartesian(0.4, 0.0, 0.2)
        
        # 5. Close gripper
        node.close_gripper()
        
        # 6. Move back to home
        node.move_to_named_pose("home")
        
        node.get_logger().info("Demo complete!")
        
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
```

---

## Gripper Control

The Gen3 Lite has an integrated 2-finger gripper controlled via the `GripperCommand` action.

### Using GripperInterface (Recommended)

```python
from pymoveit2 import GripperInterface

gripper = GripperInterface(
    node=node,
    gripper_joint_names=["right_finger_bottom_joint"],
    open_gripper_joint_positions=[0.0],
    closed_gripper_joint_positions=[0.8],
    gripper_group_name="gripper",
    callback_group=callback_group,
    gripper_command_action_name="/gen3_lite_2f_gripper_controller/gripper_cmd",
)

# Open gripper
gripper.open()
gripper.wait_until_executed()

# Close gripper
gripper.close()
gripper.wait_until_executed()

# Move to specific position
gripper.move_to_position(0.4)  # Half open
gripper.wait_until_executed()

# Toggle state
gripper.toggle()
gripper.wait_until_executed()
```

### Using GripperCommand Directly

```python
from pymoveit2 import GripperCommand

gripper = GripperCommand(
    node=node,
    gripper_joint_names=["right_finger_bottom_joint"],
    open_gripper_joint_positions=[0.0],
    closed_gripper_joint_positions=[0.8],
    max_effort=100.0,  # Max gripping force
    callback_group=callback_group,
    gripper_command_action_name="/gen3_lite_2f_gripper_controller/gripper_cmd",
)
```

### Command Line Gripper Control

```bash
# Open gripper
ros2 action send_goal /gen3_lite_2f_gripper_controller/gripper_cmd \
    control_msgs/action/GripperCommand \
    "{command:{position: 0.0, max_effort: 100.0}}"

# Close gripper
ros2 action send_goal /gen3_lite_2f_gripper_controller/gripper_cmd \
    control_msgs/action/GripperCommand \
    "{command:{position: 0.8, max_effort: 100.0}}"
```

---

## Complete Examples

### Pick and Place

```python
def pick_and_place(node: Gen3LiteMoveIt2Node):
    """Execute a pick and place operation."""
    
    # Define positions
    pick_position = (0.35, 0.15, 0.05)   # Object location
    place_position = (0.35, -0.15, 0.05)  # Target location
    approach_height = 0.15                 # Height for approach
    
    # Orientation: gripper pointing down
    orientation = (0.0, 1.0, 0.0, 0.0)  # 180° pitch
    
    # 1. Move to home and open gripper
    node.move_to_named_pose("home")
    node.open_gripper()
    
    # 2. Move above pick position
    node.move_to_cartesian(
        pick_position[0], pick_position[1], approach_height,
        *orientation
    )
    
    # 3. Move down to pick position (linear motion)
    node.move_to_cartesian(
        *pick_position, *orientation,
        cartesian=True
    )
    
    # 4. Close gripper to grasp
    node.close_gripper()
    
    # 5. Lift object
    node.move_to_cartesian(
        pick_position[0], pick_position[1], approach_height,
        *orientation,
        cartesian=True
    )
    
    # 6. Move above place position
    node.move_to_cartesian(
        place_position[0], place_position[1], approach_height,
        *orientation
    )
    
    # 7. Move down to place position
    node.move_to_cartesian(
        *place_position, *orientation,
        cartesian=True
    )
    
    # 8. Open gripper to release
    node.open_gripper()
    
    # 9. Retreat
    node.move_to_cartesian(
        place_position[0], place_position[1], approach_height,
        *orientation,
        cartesian=True
    )
    
    # 10. Return home
    node.move_to_named_pose("home")
```

### Waypoint Following

```python
def follow_waypoints(node: Gen3LiteMoveIt2Node, waypoints: list):
    """Follow a sequence of Cartesian waypoints."""
    
    # Default orientation (gripper pointing down)
    orientation = (0.0, 1.0, 0.0, 0.0)
    
    for i, waypoint in enumerate(waypoints):
        node.get_logger().info(f"Moving to waypoint {i+1}/{len(waypoints)}")
        
        success = node.move_to_cartesian(
            waypoint[0], waypoint[1], waypoint[2],
            *orientation,
            cartesian=True,
        )
        
        if not success:
            node.get_logger().error(f"Failed to reach waypoint {i+1}")
            return False
    
    return True

# Example usage
waypoints = [
    (0.3, 0.1, 0.2),
    (0.3, 0.1, 0.1),
    (0.3, -0.1, 0.1),
    (0.3, -0.1, 0.2),
    (0.3, 0.0, 0.25),
]
follow_waypoints(node, waypoints)
```

### Collision-Aware Motion

```python
def collision_aware_motion(node: Gen3LiteMoveIt2Node):
    """Demonstrate collision avoidance."""
    
    # Add table
    node.add_table(height=0.0)
    
    # Add obstacle
    node.add_box_obstacle(
        name="obstacle",
        size=(0.1, 0.1, 0.3),
        position=(0.35, 0.0, 0.15)
    )
    
    # Plan around obstacle
    node.move_to_cartesian(0.4, 0.15, 0.1)  # Left of obstacle
    node.move_to_cartesian(0.4, -0.15, 0.1) # Right of obstacle
    
    # Remove obstacle
    node.remove_obstacle("obstacle")
    
    # Move through where obstacle was
    node.move_to_cartesian(0.35, 0.0, 0.1)
```

---

## Real-Time Servo Control

For teleoperation or reactive control using MoveIt2 Servo:

```python
from pymoveit2 import MoveIt2Servo
import time

# Initialize servo interface
servo = MoveIt2Servo(
    node=node,
    frame_id="base_link",
    linear_speed=0.1,   # m/s scaling
    angular_speed=0.5,  # rad/s scaling
    callback_group=callback_group,
)

# Enable servo
servo.enable(sync=True)

# Move in +X direction for 1 second
start = time.time()
while time.time() - start < 1.0:
    servo(
        linear=(1.0, 0.0, 0.0),   # +X direction
        angular=(0.0, 0.0, 0.0),  # No rotation
    )
    time.sleep(0.01)  # 100 Hz

# Stop
servo(linear=(0.0, 0.0, 0.0), angular=(0.0, 0.0, 0.0))

# Disable servo
servo.disable(sync=True)
```

### Gamepad Teleoperation Example

```python
from sensor_msgs.msg import Joy

class TeleopController:
    def __init__(self, node, servo):
        self.servo = servo
        self.node = node
        
        # Subscribe to joystick
        node.create_subscription(
            Joy, "/joy", self.joy_callback, 10
        )
    
    def joy_callback(self, msg):
        # Map joystick axes to velocities
        # Assumes standard gamepad layout
        linear_x = msg.axes[1] * 0.1   # Left stick Y
        linear_y = msg.axes[0] * 0.1   # Left stick X
        linear_z = msg.axes[4] * 0.1   # Right stick Y
        angular_z = msg.axes[3] * 0.3  # Right stick X
        
        self.servo(
            linear=(linear_x, linear_y, linear_z),
            angular=(0.0, 0.0, angular_z),
        )
```

---

## Common Operations

### Computing Forward Kinematics

```python
# Get current end effector pose
pose = arm.compute_fk()
if pose:
    print(f"Position: {pose.pose.position}")
    print(f"Orientation: {pose.pose.orientation}")

# FK for specific joint configuration
pose = arm.compute_fk(joint_state=[0.0, -0.5, 1.0, 0.0, -0.5, 0.0])
```

### Computing Inverse Kinematics

```python
# Compute IK for a target pose
joint_state = arm.compute_ik(
    position=(0.4, 0.0, 0.2),
    quat_xyzw=(0.0, 1.0, 0.0, 0.0),
)

if joint_state:
    print(f"IK solution: {joint_state.position}")
else:
    print("No IK solution found")
```

### Switching Controllers

```bash
# Switch to twist controller (for servo)
ros2 service call /controller_manager/switch_controller \
    controller_manager_msgs/srv/SwitchController \
    "{activate_controllers: [twist_controller], 
      deactivate_controllers: [joint_trajectory_controller],
      strictness: 1, activate_asap: true}"

# Switch back to joint trajectory controller
ros2 service call /controller_manager/switch_controller \
    controller_manager_msgs/srv/SwitchController \
    "{activate_controllers: [joint_trajectory_controller], 
      deactivate_controllers: [twist_controller],
      strictness: 1, activate_asap: true}"
```

### Direct Joint Command

```bash
ros2 topic pub /joint_trajectory_controller/joint_trajectory \
    trajectory_msgs/JointTrajectory "{
        joint_names: [joint_1, joint_2, joint_3, joint_4, joint_5, joint_6],
        points: [{positions: [0, 0, 0, 0, 0, 0], time_from_start: {sec: 5}}]
    }" -1
```

---

## Troubleshooting

### Common Issues

#### 1. Cannot Connect to Robot

```bash
# Check network connectivity
ping 192.168.1.10

# Verify network interface configuration
ip addr show

# Check if kortex driver is running
ros2 node list | grep kortex
```

#### 2. MoveIt Planning Fails

```python
# Increase planning attempts and time
arm.num_planning_attempts = 20
arm.allowed_planning_time = 10.0

# Try different planner
arm.planner_id = "RRTConnect"  # or "RRTstar", "PRM", etc.
```

#### 3. Gripper Not Responding

```bash
# Check gripper action server
ros2 action list | grep gripper

# Verify controller is active
ros2 control list_controllers
```

#### 4. Robot Not Moving

```bash
# Check controller status
ros2 control list_controllers

# Verify joint_trajectory_controller is active
ros2 topic echo /joint_trajectory_controller/state
```

#### 5. Slow Motion

```python
# Increase velocity/acceleration limits
arm.max_velocity = 1.0       # 100% (use with caution)
arm.max_acceleration = 1.0
```

### Useful ROS2 Commands

```bash
# List all topics
ros2 topic list

# Echo joint states
ros2 topic echo /joint_states

# List controllers
ros2 control list_controllers

# Check TF tree
ros2 run tf2_tools view_frames

# Visualize in RViz
ros2 launch kinova_gen3_lite_moveit_config robot.launch.py robot_ip:=192.168.1.10
```

### ROS2 Topics Reference

| Topic | Type | Description |
|-------|------|-------------|
| `/joint_states` | `sensor_msgs/JointState` | Current joint states |
| `/joint_trajectory_controller/joint_trajectory` | `trajectory_msgs/JointTrajectory` | Command trajectory |
| `/joint_trajectory_controller/state` | `control_msgs/JointTrajectoryControllerState` | Controller state |
| `/gen3_lite_2f_gripper_controller/gripper_cmd` | Action | Gripper command |
| `/twist_controller/commands` | `geometry_msgs/TwistStamped` | Twist commands (servo) |

### ROS2 Services Reference

| Service | Type | Description |
|---------|------|-------------|
| `/plan_kinematic_path` | `moveit_msgs/GetMotionPlan` | Motion planning |
| `/compute_fk` | `moveit_msgs/GetPositionFK` | Forward kinematics |
| `/compute_ik` | `moveit_msgs/GetPositionIK` | Inverse kinematics |
| `/controller_manager/switch_controller` | `controller_manager_msgs/SwitchController` | Switch controllers |

---

## Additional Resources

- [ros2_kortex GitHub Repository](https://github.com/Kinovarobotics/ros2_kortex)
- [Kinova Kortex API Documentation](https://github.com/Kinovarobotics/kortex)
- [MoveIt2 Documentation](https://moveit.picknik.ai/main/index.html)
- [Kinova Product Page](https://www.kinovarobotics.com/product/gen3-lite-robots)

---

*This guide is designed for the Kinova Gen3 Lite with ROS2 Jazzy and the ros2_kortex package. Always ensure you have the latest firmware and software versions for optimal performance.*
