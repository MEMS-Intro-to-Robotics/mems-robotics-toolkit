# Lab 06: Pick & Place with Kinova Gen3 Lite

Starter code for programming a robotic arm to pick up and place objects using MoveIt2.

## Files

| File | Description |
|------|-------------|
| `pick_and_place.py` | Main starter script with MoveIt2 arm control and gripper interface |
| `spawn_blocks.sh` | Gazebo helper script to spawn table and colored blocks |

## Quick Start

1. **Launch the Kinova simulation** (in one terminal):
   ```bash
   ros2 launch kortex_bringup kortex_sim_control.launch.py start_rviz:=true
   ```

2. **Spawn the scene objects** (in another terminal):
   ```bash
   ./spawn_blocks.sh
   ```

3. **Add collision objects to MoveIt planning scene**:
   ```bash
   ros2 run lab06_moveit pick_and_place --ros-args -p task:=add_scene
   ```

4. **Run the pick and place task**:
   ```bash
   ros2 run lab06_moveit pick_and_place --ros-args -p task:=pick_place_one
   ```

## Available Tasks

Pass these via `--ros-args -p task:=<name>`:

- `home` - Move to home joint configuration
- `retract` - Move to retracted position
- `add_scene` - Add table and blocks to the planning scene
- `pick_place_one` - Execute the basic pick and place sequence

## Related Guides

- [pymoveit2 API Guide](../guides/pymoveit2_api_guide.md) - Core MoveIt2 Python reference
- [Kinova Gen3 Lite Guide](../guides/kinova_gen3_lite_moveit2_guide.md) - Robot-specific setup and configuration
- [Quick Reference](../guides/quick_reference.md) - Linux, Docker, ROS 2 basics
