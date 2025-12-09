# Multi-Robot Coordination Guide

## ROS2 Jazzy with Dual Kinova Gen3 Lite Arms

This guide covers setting up and coordinating multiple robot arms in ROS2, focusing on dual Kinova Gen3 Lite configurations. The concepts apply broadly to any multi-robot setup.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Approach Comparison](#2-approach-comparison)
3. [Network and Hardware Setup](#3-network-and-hardware-setup)
4. [Approach A: Unified URDF (Compound Robot)](#4-approach-a-unified-urdf-compound-robot)
5. [Approach B: Namespaced Robots (Independent)](#5-approach-b-namespaced-robots-independent)
6. [MoveIt2 Multi-Arm Planning](#6-moveit2-multi-arm-planning)
7. [Coordinated Motion Execution](#7-coordinated-motion-execution)
8. [Programming Patterns](#8-programming-patterns)
9. [Common Pitfalls](#9-common-pitfalls)
10. [Debugging Multi-Robot Systems](#10-debugging-multi-robot-systems)

---

## 1. Architecture Overview

### The Multi-Robot Challenge

Running multiple robots introduces complexity at every layer:

| Layer | Single Robot | Multiple Robots |
|-------|--------------|-----------------|
| **URDF** | One robot description | Prefixed links/joints OR separate URDFs |
| **TF Tree** | Single tree from world | Must connect all robots to common frame |
| **ros2_control** | One controller manager | One per robot OR one shared |
| **MoveIt2** | One planning group | Multiple groups, potentially compound |
| **Topics/Services** | Standard names | Namespaced or prefixed |

### Two Fundamental Approaches

```
Approach A: Unified URDF                    Approach B: Namespaced Robots
─────────────────────────                   ────────────────────────────
                                            
    ┌─────────────────────┐                 ┌─────────────┐  ┌─────────────┐
    │   Combined URDF     │                 │   /left/    │  │   /right/   │
    │  (left_ + right_)   │                 │   robot     │  │   robot     │
    └──────────┬──────────┘                 └──────┬──────┘  └──────┬──────┘
               │                                   │                │
    ┌──────────▼──────────┐                 ┌──────▼──────┐  ┌──────▼──────┐
    │  Single Controller  │                 │ Controller  │  │ Controller  │
    │      Manager        │                 │  Manager 1  │  │  Manager 2  │
    └──────────┬──────────┘                 └──────┬──────┘  └──────┬──────┘
               │                                   │                │
    ┌──────────▼──────────┐                 ┌──────▼──────┐  ┌──────▼──────┐
    │   MoveIt2 with      │                 │  MoveIt2    │  │  MoveIt2    │
    │   Compound Group    │                 │  Instance 1 │  │  Instance 2 │
    └─────────────────────┘                 └─────────────┘  └─────────────┘

Best for: Dual-arm manipulation,           Best for: Independent robots,
coordinated bimanual tasks                 separate workspaces, flexibility
```

---

## 2. Approach Comparison

### Approach A: Unified URDF (Compound Robot)

**Pros:**
- Single TF tree, automatic collision checking between arms
- Native support for compound planning groups
- Simpler topic structure
- Better for tightly coupled bimanual tasks

**Cons:**
- Both robots must be launched together
- Single point of failure
- More complex URDF management
- Harder to test individual arms

**Best For:**
- Dual-arm manipulation (handing objects between arms)
- Coordinated assembly tasks
- Research on bimanual coordination

### Approach B: Namespaced Robots (Independent)

**Pros:**
- Independent operation (can run one arm alone)
- Easier debugging and testing
- More flexible deployment
- Can add/remove robots dynamically

**Cons:**
- Must manually handle inter-robot collision
- Coordinating motion requires extra work
- More complex topic/service routing
- TF tree requires explicit connections

**Best For:**
- Independent workstations
- Flexible research setups
- When robots may operate independently
- Different robot types in same workspace

---

## 3. Network and Hardware Setup

### Physical Network Configuration

Each Kinova Gen3 Lite has IP address `192.168.1.10` by default. For multiple robots, you must:

**Option 1: Different Subnets (Recommended)**

```
Robot 1: 192.168.1.10  ──── NIC 1 (192.168.1.1)
                                              ├── Your Computer
Robot 2: 192.168.2.10  ──── NIC 2 (192.168.2.1)
```

Configure each NIC:
```bash
# NIC 1 for Robot 1
sudo ip addr add 192.168.1.1/24 dev eth0

# NIC 2 for Robot 2 (or USB-Ethernet adapter)
sudo ip addr add 192.168.2.1/24 dev eth1
```

**Option 2: Reassign Robot IP (Requires Kinova Web Interface)**

1. Connect to robot at default IP
2. Access web interface: `http://192.168.1.10`
3. Change IP address in network settings
4. Connect both robots to same subnet with different IPs

```
Robot 1: 192.168.1.10  ────┐
                          ├── Switch ── NIC (192.168.1.1) ── Your Computer
Robot 2: 192.168.1.11  ────┘
```

### Verifying Connectivity

```bash
# Test each robot
ping 192.168.1.10
ping 192.168.2.10  # or 192.168.1.11

# Run realsense-style enumeration if available
ros2 run kortex_driver list_devices  # (hypothetical, check actual package)
```

---

## 4. Approach A: Unified URDF (Compound Robot)

### Creating the Combined URDF

Create a new xacro file that includes both arms with prefixes:

**File: `dual_gen3_lite.urdf.xacro`**

```xml
<?xml version="1.0"?>
<robot xmlns:xacro="http://www.ros.org/wiki/xacro" name="dual_gen3_lite">
  
  <!-- World link (common base) -->
  <link name="world"/>
  
  <!-- Left arm parameters -->
  <xacro:arg name="left_robot_ip" default="192.168.1.10"/>
  <xacro:arg name="left_prefix" default="left_"/>
  
  <!-- Right arm parameters -->
  <xacro:arg name="right_robot_ip" default="192.168.2.10"/>
  <xacro:arg name="right_prefix" default="right_"/>
  
  <!-- Include the Gen3 Lite macro -->
  <xacro:include filename="$(find kortex_description)/robots/gen3_lite_macro.xacro"/>
  
  <!-- Left arm placement -->
  <joint name="world_to_left_base" type="fixed">
    <origin xyz="0 0.4 0" rpy="0 0 0"/>
    <parent link="world"/>
    <child link="$(arg left_prefix)base_link"/>
  </joint>
  
  <!-- Left arm instantiation -->
  <xacro:gen3_lite 
    prefix="$(arg left_prefix)"
    robot_ip="$(arg left_robot_ip)"
    gripper="gen3_lite_2f"/>
  
  <!-- Right arm placement -->
  <joint name="world_to_right_base" type="fixed">
    <origin xyz="0 -0.4 0" rpy="0 0 ${pi}"/>
    <parent link="world"/>
    <child link="$(arg right_prefix)base_link"/>
  </joint>
  
  <!-- Right arm instantiation -->
  <xacro:gen3_lite 
    prefix="$(arg right_prefix)"
    robot_ip="$(arg right_robot_ip)"
    gripper="gen3_lite_2f"/>
    
</robot>
```

### ros2_control Configuration

**File: `dual_ros2_controllers.yaml`**

```yaml
controller_manager:
  ros__parameters:
    update_rate: 100

    # Left arm controllers
    left_joint_trajectory_controller:
      type: joint_trajectory_controller/JointTrajectoryController
    left_joint_state_broadcaster:
      type: joint_state_broadcaster/JointStateBroadcaster
    left_gripper_controller:
      type: position_controllers/GripperActionController

    # Right arm controllers
    right_joint_trajectory_controller:
      type: joint_trajectory_controller/JointTrajectoryController
    right_joint_state_broadcaster:
      type: joint_state_broadcaster/JointStateBroadcaster
    right_gripper_controller:
      type: position_controllers/GripperActionController

# Left arm controller configuration
left_joint_trajectory_controller:
  ros__parameters:
    joints:
      - left_joint_1
      - left_joint_2
      - left_joint_3
      - left_joint_4
      - left_joint_5
      - left_joint_6
    command_interfaces:
      - position
    state_interfaces:
      - position
      - velocity
    state_publish_rate: 100.0
    action_monitor_rate: 20.0

left_joint_state_broadcaster:
  ros__parameters:
    joints:
      - left_joint_1
      - left_joint_2
      - left_joint_3
      - left_joint_4
      - left_joint_5
      - left_joint_6
      - left_right_finger_bottom_joint

# Right arm controller configuration
right_joint_trajectory_controller:
  ros__parameters:
    joints:
      - right_joint_1
      - right_joint_2
      - right_joint_3
      - right_joint_4
      - right_joint_5
      - right_joint_6
    command_interfaces:
      - position
    state_interfaces:
      - position
      - velocity
    state_publish_rate: 100.0
    action_monitor_rate: 20.0

right_joint_state_broadcaster:
  ros__parameters:
    joints:
      - right_joint_1
      - right_joint_2
      - right_joint_3
      - right_joint_4
      - right_joint_5
      - right_joint_6
      - right_right_finger_bottom_joint
```

### SRDF for MoveIt2 (Planning Groups)

**File: `dual_gen3_lite.srdf`**

```xml
<?xml version="1.0" ?>
<robot name="dual_gen3_lite">
  
  <!-- Left arm group -->
  <group name="left_arm">
    <joint name="left_joint_1"/>
    <joint name="left_joint_2"/>
    <joint name="left_joint_3"/>
    <joint name="left_joint_4"/>
    <joint name="left_joint_5"/>
    <joint name="left_joint_6"/>
  </group>
  
  <!-- Right arm group -->
  <group name="right_arm">
    <joint name="right_joint_1"/>
    <joint name="right_joint_2"/>
    <joint name="right_joint_3"/>
    <joint name="right_joint_4"/>
    <joint name="right_joint_5"/>
    <joint name="right_joint_6"/>
  </group>
  
  <!-- Compound group for both arms -->
  <group name="both_arms">
    <group name="left_arm"/>
    <group name="right_arm"/>
  </group>
  
  <!-- Left gripper -->
  <group name="left_gripper">
    <joint name="left_right_finger_bottom_joint"/>
  </group>
  
  <!-- Right gripper -->
  <group name="right_gripper">
    <joint name="right_right_finger_bottom_joint"/>
  </group>
  
  <!-- End effectors -->
  <end_effector name="left_ee" parent_link="left_end_effector_link" group="left_gripper"/>
  <end_effector name="right_ee" parent_link="right_end_effector_link" group="right_gripper"/>
  
  <!-- Disable collisions between adjacent links -->
  <disable_collisions link1="left_base_link" link2="left_shoulder_link" reason="Adjacent"/>
  <!-- ... add all adjacent link pairs ... -->
  
  <!-- Optionally disable collisions between arms if they can't reach each other -->
  <!-- <disable_collisions link1="left_base_link" link2="right_base_link" reason="Never"/> -->
  
</robot>
```

---

## 5. Approach B: Namespaced Robots (Independent)

### Launch File Structure

Each robot runs in its own namespace with independent nodes:

**File: `dual_robots_namespaced.launch.py`**

```python
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    GroupAction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import PushRosNamespace, Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    
    # Arguments
    left_robot_ip = LaunchConfiguration('left_robot_ip', default='192.168.1.10')
    right_robot_ip = LaunchConfiguration('right_robot_ip', default='192.168.2.10')
    use_fake_hardware = LaunchConfiguration('use_fake_hardware', default='true')
    
    # Left robot group (namespaced)
    left_robot = GroupAction([
        PushRosNamespace('left'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                PathJoinSubstitution([
                    FindPackageShare('kinova_gen3_lite_moveit_config'),
                    'launch',
                    'robot.launch.py'
                ])
            ]),
            launch_arguments={
                'robot_ip': left_robot_ip,
                'use_fake_hardware': use_fake_hardware,
                'prefix': 'left_',
            }.items()
        ),
    ])
    
    # Right robot group (namespaced)
    right_robot = GroupAction([
        PushRosNamespace('right'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                PathJoinSubstitution([
                    FindPackageShare('kinova_gen3_lite_moveit_config'),
                    'launch',
                    'robot.launch.py'
                ])
            ]),
            launch_arguments={
                'robot_ip': right_robot_ip,
                'use_fake_hardware': use_fake_hardware,
                'prefix': 'right_',
            }.items()
        ),
    ])
    
    # Static transform connecting both robots to world
    left_to_world = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        arguments=['0', '0.4', '0', '0', '0', '0', 'world', 'left/left_base_link'],
    )
    
    right_to_world = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        arguments=['0', '-0.4', '0', '0', '0', '3.14159', 'world', 'right/right_base_link'],
    )
    
    return LaunchDescription([
        DeclareLaunchArgument('left_robot_ip', default_value='192.168.1.10'),
        DeclareLaunchArgument('right_robot_ip', default_value='192.168.2.10'),
        DeclareLaunchArgument('use_fake_hardware', default_value='true'),
        left_robot,
        right_robot,
        left_to_world,
        right_to_world,
    ])
```

### Topic Structure with Namespaces

After launching, you'll have parallel topic structures:

```
/left/joint_states
/left/joint_trajectory_controller/follow_joint_trajectory
/left/move_group/...
/left/controller_manager/...

/right/joint_states
/right/joint_trajectory_controller/follow_joint_trajectory
/right/move_group/...
/right/controller_manager/...
```

### Interacting with Namespaced Controllers

```bash
# List controllers for left robot
ros2 control list_controllers -c /left/controller_manager

# List controllers for right robot
ros2 control list_controllers -c /right/controller_manager

# Switch controllers (must specify controller manager)
ros2 control switch_controllers \
    -c /left/controller_manager \
    --activate joint_trajectory_controller \
    --deactivate forward_position_controller
```

---

## 6. MoveIt2 Multi-Arm Planning

### Planning with Compound Groups (Approach A)

```python
from moveit.planning import MoveItPy
from moveit.core.robot_state import RobotState

# Initialize MoveItPy
moveit = MoveItPy(node_name="dual_arm_planner")

# Get planning components for different groups
left_arm = moveit.get_planning_component("left_arm")
right_arm = moveit.get_planning_component("right_arm")
both_arms = moveit.get_planning_component("both_arms")

# Plan for left arm only
left_arm.set_start_state_to_current_state()
left_arm.set_goal_state(configuration_name="home")
plan = left_arm.plan()

# Plan for both arms simultaneously
both_arms.set_start_state_to_current_state()

# Set goals for both end effectors
robot_state = RobotState(moveit.get_robot_model())
robot_state.set_from_ik("left_arm", left_target_pose, "left_tool_frame")
robot_state.set_from_ik("right_arm", right_target_pose, "right_tool_frame")
both_arms.set_goal_state(robot_state=robot_state)

plan = both_arms.plan()
```

### Planning with pymoveit2 (Per-Arm)

```python
from pymoveit2 import MoveIt2

# Left arm interface
left_moveit = MoveIt2(
    node=node,
    joint_names=[f"left_joint_{i}" for i in range(1, 7)],
    base_link_name="left_base_link",
    end_effector_name="left_tool_frame",
    group_name="left_arm",
    callback_group=callback_group,
)

# Right arm interface  
right_moveit = MoveIt2(
    node=node,
    joint_names=[f"right_joint_{i}" for i in range(1, 7)],
    base_link_name="right_base_link",
    end_effector_name="right_tool_frame",
    group_name="right_arm",
    callback_group=callback_group,
)

# Plan independently
left_moveit.move_to_pose(position=(0.3, 0.5, 0.2), quat_xyzw=(0, 1, 0, 0))
right_moveit.move_to_pose(position=(0.3, -0.5, 0.2), quat_xyzw=(0, 1, 0, 0))
```

### Collision-Aware Planning Between Arms

When using separate planning for each arm, you must add the other arm as a collision object:

```python
def add_other_arm_as_collision(moveit2, other_arm_joint_states, other_arm_urdf_links):
    """Add the other robot arm as collision geometry."""
    
    # Option 1: Add simplified collision boxes at current link positions
    for link_name, pose in get_link_poses(other_arm_joint_states):
        moveit2.add_collision_box(
            id=f"other_arm_{link_name}",
            size=get_link_collision_size(link_name),
            position=pose.position,
            quat_xyzw=pose.orientation,
        )
    
    # Option 2: Use attached collision object (more accurate but complex)
    # This requires publishing the other arm's geometry to the planning scene
```

---

## 7. Coordinated Motion Execution

### Synchronous Execution

Execute both arms simultaneously with synchronized timing:

```python
import threading
from concurrent.futures import ThreadPoolExecutor

def execute_synchronized(left_moveit, right_moveit, left_traj, right_traj):
    """Execute both trajectories simultaneously."""
    
    # Ensure trajectories have same duration
    max_duration = max(
        get_trajectory_duration(left_traj),
        get_trajectory_duration(right_traj)
    )
    
    left_traj = retime_trajectory(left_traj, max_duration)
    right_traj = retime_trajectory(right_traj, max_duration)
    
    # Execute in parallel
    with ThreadPoolExecutor(max_workers=2) as executor:
        left_future = executor.submit(left_moveit.execute, left_traj)
        right_future = executor.submit(right_moveit.execute, right_traj)
        
        # Wait for both
        left_result = left_future.result()
        right_result = right_future.result()
    
    return left_result and right_result
```

### Sequential Coordination

For handoff tasks where one arm must complete before the other starts:

```python
def handoff_object(left_moveit, right_moveit, left_gripper, right_gripper, 
                   handoff_position):
    """Coordinate object handoff between arms."""
    
    # 1. Left arm moves to handoff position (holding object)
    left_moveit.move_to_pose(position=handoff_position, ...)
    left_moveit.wait_until_executed()
    
    # 2. Right arm approaches handoff position
    approach_pos = (handoff_position[0], handoff_position[1], handoff_position[2] + 0.1)
    right_moveit.move_to_pose(position=approach_pos, ...)
    right_moveit.wait_until_executed()
    
    # 3. Right arm moves to grasp position
    right_moveit.move_to_pose(position=handoff_position, ...)
    right_moveit.wait_until_executed()
    
    # 4. Right gripper closes
    right_gripper.close()
    right_gripper.wait_until_executed()
    
    # 5. Left gripper opens (transfers object)
    left_gripper.open()
    left_gripper.wait_until_executed()
    
    # 6. Arms retreat
    right_moveit.move_to_pose(position=approach_pos, ...)
    left_moveit.move_to_configuration([0, 0, 0, 0, 0, 0])  # Home
    
    # Wait for both
    right_moveit.wait_until_executed()
    left_moveit.wait_until_executed()
```

### Asynchronous Coordination with State Machine

```python
from enum import Enum, auto

class DualArmState(Enum):
    IDLE = auto()
    LEFT_MOVING = auto()
    RIGHT_MOVING = auto()
    BOTH_MOVING = auto()
    COORDINATING = auto()

class DualArmCoordinator:
    def __init__(self, left_moveit, right_moveit):
        self.left = left_moveit
        self.right = right_moveit
        self.state = DualArmState.IDLE
        
    def update(self):
        """Call periodically to manage state transitions."""
        left_busy = self.left.query_state() == MoveIt2State.EXECUTING
        right_busy = self.right.query_state() == MoveIt2State.EXECUTING
        
        if left_busy and right_busy:
            self.state = DualArmState.BOTH_MOVING
        elif left_busy:
            self.state = DualArmState.LEFT_MOVING
        elif right_busy:
            self.state = DualArmState.RIGHT_MOVING
        else:
            self.state = DualArmState.IDLE
    
    def is_safe_to_move(self, arm: str) -> bool:
        """Check if it's safe to start a motion."""
        # Implement collision checking logic here
        return True
    
    def move_left_async(self, target_pose):
        if self.is_safe_to_move('left'):
            self.left.move_to_pose(**target_pose)
    
    def move_right_async(self, target_pose):
        if self.is_safe_to_move('right'):
            self.right.move_to_pose(**target_pose)
```

---

## 8. Programming Patterns

### Pattern 1: Robot-Agnostic Interface

Create an abstraction layer that works regardless of which robot:

```python
class ArmInterface:
    """Abstract interface for a single arm."""
    
    def __init__(self, node, namespace: str, prefix: str):
        self.namespace = namespace
        self.prefix = prefix
        
        joint_names = [f"{prefix}joint_{i}" for i in range(1, 7)]
        
        self.moveit = MoveIt2(
            node=node,
            joint_names=joint_names,
            base_link_name=f"{prefix}base_link",
            end_effector_name=f"{prefix}tool_frame",
            group_name=f"{prefix}arm" if prefix else "manipulator",
            callback_group=ReentrantCallbackGroup(),
        )
    
    def move_to_pose(self, pose):
        self.moveit.move_to_pose(**pose)
        return self.moveit.wait_until_executed()
    
    def move_to_named(self, name: str):
        # Map named poses to configurations
        poses = {
            'home': [0, 0, 0, 0, 0, 0],
            'ready': [0, -0.5, 1.0, 0, -0.5, 0],
        }
        self.moveit.move_to_configuration(poses[name])
        return self.moveit.wait_until_executed()


class DualArmSystem:
    """Manages two arms with consistent interface."""
    
    def __init__(self, node):
        self.left = ArmInterface(node, namespace='left', prefix='left_')
        self.right = ArmInterface(node, namespace='right', prefix='right_')
        self.arms = {'left': self.left, 'right': self.right}
    
    def get_arm(self, name: str) -> ArmInterface:
        return self.arms[name]
    
    def home_all(self):
        """Send all arms to home position."""
        for arm in self.arms.values():
            arm.move_to_named('home')
```

### Pattern 2: Task-Based Coordination

```python
class BimanualTask:
    """Base class for bimanual tasks."""
    
    def __init__(self, dual_arm_system):
        self.system = dual_arm_system
    
    def execute(self):
        raise NotImplementedError


class PickAndHandoff(BimanualTask):
    """Pick with left, hand to right, place with right."""
    
    def __init__(self, dual_arm_system, pick_pose, place_pose, handoff_pose):
        super().__init__(dual_arm_system)
        self.pick_pose = pick_pose
        self.place_pose = place_pose
        self.handoff_pose = handoff_pose
    
    def execute(self):
        left = self.system.left
        right = self.system.right
        
        # Phase 1: Pick
        left.move_to_pose(approach(self.pick_pose))
        left.move_to_pose(self.pick_pose)
        left.close_gripper()
        left.move_to_pose(retreat(self.pick_pose))
        
        # Phase 2: Handoff
        left.move_to_pose(self.handoff_pose)
        right.move_to_pose(approach(self.handoff_pose))
        right.move_to_pose(self.handoff_pose)
        right.close_gripper()
        left.open_gripper()
        
        # Phase 3: Place
        left.move_to_named('home')
        right.move_to_pose(approach(self.place_pose))
        right.move_to_pose(self.place_pose)
        right.open_gripper()
        right.move_to_pose(retreat(self.place_pose))
        right.move_to_named('home')
```

### Pattern 3: Collision-Aware Planning Service

```python
class CollisionAwarePlanner:
    """Plans motions while considering the other arm."""
    
    def __init__(self, left_moveit, right_moveit, planning_scene):
        self.left = left_moveit
        self.right = right_moveit
        self.scene = planning_scene
    
    def plan_with_other_arm_static(self, moving_arm: str, target):
        """Plan for one arm while treating the other as obstacle."""
        
        if moving_arm == 'left':
            planner = self.left
            obstacle_arm = self.right
        else:
            planner = self.right
            obstacle_arm = self.left
        
        # Get current state of obstacle arm
        obstacle_state = obstacle_arm.get_current_state()
        
        # Add obstacle arm geometry to planning scene
        self._add_arm_to_scene(obstacle_arm, obstacle_state)
        
        # Plan
        trajectory = planner.plan(**target)
        
        # Clean up
        self._remove_arm_from_scene(obstacle_arm)
        
        return trajectory
    
    def _add_arm_to_scene(self, arm, state):
        """Add arm links as collision objects."""
        # Implementation depends on your collision geometry approach
        pass
    
    def _remove_arm_from_scene(self, arm):
        """Remove arm collision objects."""
        pass
```

---

## 9. Common Pitfalls

### Pitfall 1: TF Frame Conflicts

**Problem:** Both robots publish `base_link`, causing TF conflicts.

**Solution:** Always use prefixes:
```xml
<!-- In URDF/xacro -->
<link name="${prefix}base_link"/>
```

### Pitfall 2: Joint State Topic Collision

**Problem:** Both robots publish to `/joint_states`.

**Solution A (Unified):** Single combined joint state with all prefixed joints.

**Solution B (Namespaced):** 
```
/left/joint_states
/right/joint_states
```

If you need a combined view:
```bash
# Use joint_state_publisher to combine
ros2 run joint_state_publisher joint_state_publisher \
    --ros-args -r /joint_states:=/combined_joint_states \
    -p source_list:="['/left/joint_states', '/right/joint_states']"
```

### Pitfall 3: Controller Manager Confusion

**Problem:** `ros2 control` commands go to wrong controller manager.

**Solution:** Always specify the controller manager:
```bash
ros2 control list_controllers -c /left/controller_manager
```

### Pitfall 4: MoveIt Planning Scene Not Shared

**Problem:** Left arm doesn't know about right arm's collision geometry.

**Solution:** For compound groups, use single MoveIt instance. For separate instances, manually synchronize planning scenes or add the other arm as collision objects.

### Pitfall 5: Timing Synchronization

**Problem:** Arms reach different points at different times.

**Solution:** Retime trajectories to match duration:
```python
def synchronize_trajectories(traj1, traj2):
    """Adjust both trajectories to same duration."""
    dur1 = traj1.points[-1].time_from_start
    dur2 = traj2.points[-1].time_from_start
    
    target_duration = max(dur1, dur2)
    
    scale1 = target_duration / dur1
    scale2 = target_duration / dur2
    
    # Scale time_from_start for each point
    for point in traj1.points:
        point.time_from_start = scale_duration(point.time_from_start, scale1)
    for point in traj2.points:
        point.time_from_start = scale_duration(point.time_from_start, scale2)
    
    return traj1, traj2
```

### Pitfall 6: Emergency Stop Handling

**Problem:** E-stop on one robot doesn't stop the other.

**Solution:** Implement coordinated safety:
```python
class SafetyMonitor:
    def __init__(self, arms):
        self.arms = arms
        self.emergency_stop = False
    
    def check_safety(self):
        for arm in self.arms:
            if arm.is_faulted():
                self.trigger_emergency_stop()
    
    def trigger_emergency_stop(self):
        self.emergency_stop = True
        for arm in self.arms:
            arm.cancel_execution()
            arm.stop()
```

---

## 10. Debugging Multi-Robot Systems

### Visualizing TF Trees

```bash
# View the complete TF tree
ros2 run tf2_tools view_frames

# Check specific transforms
ros2 run tf2_ros tf2_echo world left_base_link
ros2 run tf2_ros tf2_echo world right_base_link
ros2 run tf2_ros tf2_echo left_tool_frame right_tool_frame
```

### Listing All Topics by Namespace

```bash
# All topics
ros2 topic list

# Filter by namespace
ros2 topic list | grep "^/left"
ros2 topic list | grep "^/right"

# Check specific topic info
ros2 topic info /left/joint_states
ros2 topic info /right/joint_states
```

### Controller Status

```bash
# Left robot controllers
ros2 control list_controllers -c /left/controller_manager
ros2 control list_hardware_interfaces -c /left/controller_manager

# Right robot controllers
ros2 control list_controllers -c /right/controller_manager
ros2 control list_hardware_interfaces -c /right/controller_manager
```

### RViz Configuration for Dual Arms

Create an RViz config that shows both robots:

1. Add RobotModel display for each robot
   - Set Robot Description topic appropriately
   - Set TF Prefix if using namespaces

2. Add MotionPlanning display
   - Configure for compound group or individual arm

3. Add TF display
   - Enable relevant frames

### Debugging Planning Failures

```python
def debug_planning(moveit, target):
    """Debug why planning might fail."""
    
    # Check if target is reachable
    ik_solution = moveit.compute_ik(
        position=target['position'],
        quat_xyzw=target['quat_xyzw']
    )
    
    if ik_solution is None:
        print("ERROR: No IK solution found - target may be unreachable")
        return
    
    # Check for collisions at target
    # (Requires access to planning scene)
    
    # Try planning with more attempts
    moveit.num_planning_attempts = 20
    moveit.allowed_planning_time = 10.0
    
    trajectory = moveit.plan(**target)
    
    if trajectory is None:
        print("ERROR: Planning failed even with extended time")
        print("Check: collision objects, joint limits, planning scene state")
```

---

## References

- [MoveIt2 Dual Arms Tutorial](https://moveit.picknik.ai/main/doc/examples/dual_arms/dual_arms_tutorial.html)
- [ros2_control Example 15: Multiple Controller Managers](https://control.ros.org/master/doc/ros2_control_demos/example_15/doc/userdoc.html)
- [ros2_kortex Documentation](https://github.com/Kinovarobotics/ros2_kortex)
- [ROS2 Launch Namespaces](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Launch/Using-ROS2-Launch-For-Large-Projects.html)

---

*This guide is intended for the Duke Robotics Lab. Specific configurations may need adjustment based on your physical setup and network configuration.*
