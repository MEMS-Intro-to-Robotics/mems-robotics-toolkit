# Lab 07: 3D Goal Controller

Starter code for implementing a PID-based position controller for a Crazyflie quadrotor in 3D space.

## Files

| File | Description |
|------|-------------|
| `3d_goal_control.py` | Main PID controller node with TF integration and world-to-body frame conversion |
| `plotting.py` | Trajectory plotter that logs data and generates performance plots |
| `trajectory_publisher.py` | Helper for publishing reference trajectories |

## Quick Start

1. **Launch the Crazyflie simulation** (follow lab instructions for simulator setup)

2. **Run the controller with your tuned gains**:
   ```bash
   ros2 run <your_pkg> goal_3d_controller --ros-args \
     -p kp_x:=0.6 -p kd_x:=0.12 \
     -p kp_y:=0.6 -p kd_y:=0.12 \
     -p kp_z:=1.2 -p kd_z:=0.25
   ```

3. **Run the plotter** (in another terminal) to record performance:
   ```bash
   ros2 run <your_pkg> trajectory_plotter
   ```

4. **Publish a goal** to `/goal_pose` and observe the response.

## Tuning Hints

- Start with **P only** (kp). Raise until brisk movement with limited overshoot.
- Add **D** (kd) to reduce oscillations.
- Keep `max_v_*` low at first (e.g., 0.5 m/s), then increase once stable.
- **I** (ki) is usually small or zero for this task.

## Controller Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `kp_x`, `kp_y`, `kp_z` | 0.0 | Proportional gains (you must tune these) |
| `ki_x`, `ki_y`, `ki_z` | 0.0 | Integral gains |
| `kd_x`, `kd_y`, `kd_z` | 0.0 | Derivative gains |
| `max_v_x`, `max_v_y`, `max_v_z` | 1.0 | Velocity limits (m/s) |
| `tol_xy_m`, `tol_z_m` | 0.03 | Position tolerance for "reached" (m) |
| `control_rate_hz` | 30.0 | Control loop frequency |

## Related Guides

- [Quick Reference](../guides/quick_reference.md) - Linux, Docker, ROS 2 basics
- [Velocity Controlled Joint Motion](../guides/velocity_controlled_joint_motion_guide.md) - Low-level velocity control patterns
