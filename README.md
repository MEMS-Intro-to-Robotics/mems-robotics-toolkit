# MEMS Robotics Toolkit

This repository hosts the shared **setup scripts** and **prebuilt Docker images** used across Duke’s **Intro to Robotics** (ECE 383 / ME 555). It’s the “base camp” for your dev environment so every student starts from the same, working stack.

**Who this is for**

* Students working on labs in a Duke VCM (FastX) session.
* TAs/instructors maintaining the standard images and starter assets.

**What’s inside**

* **Docker images**: course-standard ROS 2 Jazzy environments

  * `...:base-jazzy-latest` – generic ROS 2 + dev utils
  * `...:kinova-jazzy-latest` – adds Kinova + MoveIt 2 sim stack
* **Configs & examples**: RViz presets, launch helpers, and small utilities.
* **Docs**: quick-starts and living references (this README).

## Table of Contents

[[_TOC_]]

## Quick start (3 steps)

1. **Open a GUI session** on your VCM via FastX, then on the VM:

```bash
xhost +local:docker
```

2. **Pull the course image(s)**:

```bash
docker pull gitlab-registry.oit.duke.edu/introtorobotics/mems-robotics-toolkit:base-jazzy-latest
docker pull gitlab-registry.oit.duke.edu/introtorobotics/mems-robotics-toolkit:kinova-jazzy-latest
```

3. **Run a container** with your workspace mounted:

```bash
cd ~/workspaces
docker run --rm -it --name rdev \
  --net=host \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v $PWD:/workspaces \
  gitlab-registry.oit.duke.edu/introtorobotics/mems-robotics-toolkit:base-jazzy-latest bash
```

> You'll need to switch the tag to the appropriate platform as documented in the lab manuals.

**Updating later:** pull again with the same tag to get the latest toolchain.

**Good to know**

* Don’t `apt install` inside containers unless the lab says so; the images already include dependencies.
* Keep your **personal lab repo** separate under `~/workspaces/<netid>_robotics_fall2025`.
* If GUIs don’t show up from the container, re-run `xhost +local:docker` on the VM.

**Getting help**

* First: see the **Quick Reference** below.
* Then: check your lab PDF, and course Ed/Teams for known issues.
* Still stuck? Open an issue on this repo with your image tag, commands, and logs.

---


# ROS 2 / Linux / Git Quick Reference


Assume you’re on your Duke VCM **inside the course Docker container** unless noted. Use `$ROS_DISTRO` (e.g., `jazzy`).

---

## 0) Getting onto your VM desktop (FastX)

Open **FastX 4** on your laptop → SSH to your VCM host (`vcm-xxxxx.vm.duke.edu`) with your NetID.
**Session command:** `startxfce4`  (**Window Mode:** Single)

---

## 1) Linux essentials (must-know)

**Navigation & files**

```bash
pwd                         # where am I
ls -lah                     # list (human sizes, show dotfiles)
cd /path/to/dir             # change directory
mkdir -p my/dir/structure   # make dirs (parents)
rm -i file.txt              # remove (prompt)
rm -rI mydir                # recursive, confirm once
mv old new                  # move/rename
cp -r src/ dst/             # copy dir
```

**Viewing & searching**

```bash
less file.txt               # q quit, /pattern search
grep -R "pattern" .         # recursive grep
find . -name "*.py"         # find by name
head -n 20 file.log         # first lines
tail -f file.log            # follow
```

**Editing**

```bash
nano file.txt               # Ctrl+O write, Ctrl+X exit
code .                      # open VS Code (VM GUI)
```

**Permissions & executables**

```bash
chmod +x script.sh
./script.sh
```

**Pipes, redirects, jobs**

```bash
cmd1 | cmd2                 # pipe
cmd > out.txt 2>&1          # redirect stdout+stderr
# Shortcuts: Ctrl+C (interrupt), Ctrl+Z (suspend), fg/bg (resume)
```

**Network + system quick checks**

```bash
hostname -I                 # IP(s)
ping -c 3 google.com        # connectivity
df -h                       # disk usage
free -h                     # memory
```

**Pro tips:** `Ctrl+A/E` (line start/end), `Alt+B/F` (word back/forward), `Ctrl+R` (history search), `!!` (last cmd), `!$` (last arg).
**Avoid** `sudo apt …` inside course containers unless instructed; images already include what you need.

---

## 2) Git basics (SSH workflow)

**First-time setup on the VM**

```bash
ssh-keygen -t ed25519 -C "netid@duke.edu"
ssh-add ~/.ssh/id_ed25519
cat ~/.ssh/id_ed25519.pub     # paste into GitLab → Preferences → SSH Keys
ssh -T git@gitlab.oit.duke.edu  # should say "Welcome to GitLab..."
```

**Everyday flow**

```bash
git clone git@gitlab.oit.duke.edu:<netid>/<netid>_robotics_fall2025.git
cd <netid>_robotics_fall2025

git status
git add <files>
git commit -m "meaningful message"
git push origin main
```

**Branching (lightweight)**

```bash
git switch -c feature/x
git switch main
git merge feature/x
```

**Undo cookbook**

```bash
git restore --staged <file>       # unstage
git restore <file>                # discard local (careful)
git commit --amend --no-edit      # fix last commit
```

**.gitignore essentials**

```
*.log
__pycache__/
.vscode/
```

**When `git push` is rejected (remote ahead): safe sync**

```bash
git status && git branch -vv
git add -A && git commit -m "WIP: lab updates"   # or: git stash push -u -m "WIP"
git fetch origin
git rebase origin/main    # or: git merge origin/main
# resolve conflicts → git add <file> → git rebase --continue
git push origin main
```

**Throw away local, match GitLab (destructive)**

```bash
git fetch origin
git reset --hard origin/main
```

---

## 3) Docker (using the course image)

**Enable X11 (VM, outside container)**

```bash
xhost +local:docker
```

**Start a container (bind your workspace)**

```bash
cd ~/workspaces
docker run --rm -it --name rdev \
  --net=host \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v $PWD:/workspaces \
  gitlab-registry.oit.duke.edu/introtorobotics/mems-robotics-toolkit:base-jazzy-latest bash
# For Kinova labs, use :kinova-jazzy-latest when instructed.
```

**Attach another shell**

```bash
docker exec -it rdev bash
```

**Handy Docker admin**

```bash
docker ps
docker images
docker pull gitlab-registry...:base-jazzy-latest
```

`--rm` deletes the container on exit. Omit it if you want to `docker start -ai rdev` later.

---

## 4) Terminator (multi-pane terminal inside container)

* **Split panes:** `Ctrl+Shift+O` (horizontal), `Ctrl+Shift+E` (vertical)
* **New tab:** `Ctrl+Shift+T` **Switch panes:** `Ctrl+Shift+Arrow`
* Right-click → **Profiles** to tweak fonts/colors.

---

## 5) ROS 2 essentials (generic, package-agnostic)

**Environment**

```bash
echo $ROS_DISTRO
source /opt/ros/$ROS_DISTRO/setup.bash
printenv | grep -E "^ROS_|RMW|DOMAIN"
```

**Introspection**

```bash
ros2 --help
ros2 doctor
ros2 daemon stop && ros2 daemon start   # refresh discovery

ros2 pkg list | wc -l
ros2 pkg executables <package>

ros2 node list
ros2 topic list
ros2 service list
ros2 param list
```

**Interfaces & messages**

```bash
ros2 interface list | head
ros2 interface show std_msgs/msg/String
```

**Run, echo, publish (neutral examples)**

```bash
ros2 run <package> <executable>
ros2 topic echo /chatter --qos-profile system --once
ros2 topic pub /example std_msgs/msg/String '{data: "hello"}' --once
```

**Parameters**

```bash
ros2 param describe /node param_name
ros2 param get /node param_name
ros2 param set /node param_name value
```

**Launch files**

```bash
ros2 launch <package> <file>.launch.py --show-args
```

**Recording (rosbag2)**

```bash
ros2 bag record /topic_a /topic_b   # Ctrl+C to stop
ros2 bag info <bag_dir>
ros2 bag play <bag_dir>
```

**Domain ID (multi-team isolation)**

```bash
printenv ROS_DOMAIN_ID
export ROS_DOMAIN_ID=10    # TEMP for this shell
```

---

## 6) Creating a ROS 2 Python package

```bash
# inside your workspace src/ folder
ros2 pkg create --build-type ament_python my_pkg --license MIT --dependencies rclpy

# build + source overlay (from workspace root)
colcon build --symlink-install
source install/setup.bash

# run your node
ros2 run my_pkg my_node
```

**Layout**

```
my_ws/
├── src/my_pkg/
│   ├── package.xml
│   ├── setup.cfg
│   ├── setup.py
│   └── my_pkg/my_node.py
└── install/  # generated after build
```

Re-source `install/setup.bash` in **every new terminal**.

---

## 7) Troubleshooting (quick fixes)

* **No GUI apps from container** → run `xhost +local:docker`; make sure `-v /tmp/.X11-unix` and `-e DISPLAY=$DISPLAY` are in `docker run`.
* **`ros2` sees nothing** → `ros2 daemon stop && ros2 daemon start`; confirm nodes are launched; check `ROS_DOMAIN_ID` matches.
* **Script won’t run** → `chmod +x`; ensure shebang (`#!/usr/bin/env bash` or `python3`).
* **Wrong window** → run commands in the **Terminator** you launched.
* **`git push` denied** → confirm **SSH** remote; add SSH key; push to `main`.
* **Path confusion** → use `pwd`, absolute paths; inspect `PATH` / `PYTHONPATH`.

---

## 8) Quality-of-life tips

* VS Code: use integrated terminal; install Python extension; enable **format-on-save**.
* Command history: `history | grep <term>` to find old commands.
* **Aliases** (append to `~/.bashrc` on the VM):

  ```bash
  alias cb='colcon build --symlink-install'
  alias srcros='source /opt/ros/$ROS_DISTRO/setup.bash'
  ```
* Where does a package live? `ros2 pkg prefix <pkg>`
* Git hygiene: commit small, frequent changes; write messages that say **why**, not just what.

---

## 9) MoveIt 2 + RViz (Lab-ready essentials)

**Launch the Kinova sim with RViz (example):**

```bash
ros2 launch kortex_bringup kortex_sim_control.launch.py start_rviz:=true
```

**Show trajectories clearly in RViz:**

* Displays → **MotionPlanning** → Planned Path: enable **Show Trail**, (optional) **Loop Animation**.
* Increase **Trajectory Line Width**, reduce **Robot Alpha** (ghosted look).
* Fixed Frame should match your planning frame (often `world` or `base_link`).

**Quick check that MoveIt is alive:**

```bash
ros2 node list | grep move_group
ros2 topic info /display_planned_path
```

---

## 10) Discovering names you must use (joints, groups, frames)

**URDF (robot model)**

```bash
ros2 param get /robot_state_publisher robot_description > urdf.xml
```

**SRDF (planning groups, named states, EE links)**

```bash
ros2 param get /move_group robot_description_semantic > srdf.xml
```

Open the files to confirm:

* **Joint order** for joint arrays (SRDF order).
* **Planning groups** (e.g., `arm`, `gripper`).
* **End-effector link** name.

**Live joint stream**

```bash
ros2 topic echo /joint_states --once
ros2 topic hz /joint_states
```

**TF frames (planning vs. tool)**

```bash
ros2 run tf2_ros tf2_echo base_link end_effector_link
# If available:
ros2 run tf2_tools view_frames   # creates frames.pdf
```

---

## 11) ros2\_control (can you execute?)

**List controllers**

```bash
ros2 control list_controllers
```

You should see an arm **trajectory** controller and a **gripper** controller in **active** state.

**Hardware interfaces**

```bash
ros2 control list_hardware_interfaces
```

If planning works but **execution** never starts, a controller is often **inactive** or misnamed.

---

## 12) Gripper actions (discover the action name + type)

**Find the gripper action**

```bash
ros2 action list | grep -i gripper
```

**Inspect**

```bash
ros2 action info /PATH/TO/gripper_cmd
ros2 interface show control_msgs/action/GripperCommand
```

Use the discovered action name in your `GripperInterface` init (see lab appendix).

---

## 13) Planning scene + Cartesian path sanity

**Is the scene updating?**

```bash
ros2 topic info /monitored_planning_scene
# echoing is noisy, but you can do one-shot:
ros2 topic echo /monitored_planning_scene --once
```

**Plan fraction (Cartesian)**

* `fraction ∈ [0,1]` = proportion of waypoints that were IK-feasible & collision-free.
* If low: decrease waypoint spacing, keep orientation fixed, avoid singular stretches, confirm obstacles aren’t inside your waypoints.

---

## 14) Colcon overlays & cleanup

**Rebuild the overlay & source**

```bash
colcon build --symlink-install
source install/setup.bash
```

**When weird import/path issues happen (last resort)**

```bash
rm -rf build/ install/ log/
colcon build --symlink-install
source install/setup.bash
```

---

## 15) Handy “copy block”

```bash
# Models
ros2 param get /robot_state_publisher robot_description > urdf.xml
ros2 param get /move_group robot_description_semantic > srdf.xml

# Live state
ros2 topic echo /joint_states --once
ros2 run tf2_ros tf2_echo base_link end_effector_link

# MoveIt signals
ros2 topic info /display_planned_path
ros2 topic info /monitored_planning_scene

# Controllers
ros2 control list_controllers
ros2 control list_hardware_interfaces

# Gripper action
ros2 action list | grep -i gripper
ros2 action info /PATH/TO/gripper_cmd
ros2 interface show control_msgs/action/GripperCommand
```

---

## `pymoveit2` Quick Reference

Values shown as `...` or `UPPER_SNAKE_CASE` must be replaced with names from **your** robot (URDF/SRDF, RViz TF tree, controller names). Linear units are **meters**, angles are **radians**, and quaternions are **(x, y, z, w)** unless otherwise noted.

---

### 1) Node + executor pattern (don’t block callbacks)

Keep the ROS callbacks (planning-scene updates, action feedback, logs) responsive while your milestone code runs sequentially.

```python
class YourNode(rclpy.node.Node):
    def __init__(self):
        super().__init__("YOUR_NODE_NAME")
        # self.moveit2 = ...
        # self.gripper = ...
        # self.retract_joints = None

def main():
    rclpy.init()
    node = YourNode()
    exec = rclpy.executors.MultiThreadedExecutor(num_threads=2)
    exec.add_node(node)
    threading.Thread(target=exec.spin, daemon=True).start()

    # node.example_node

    rclpy.shutdown()
```

**What this sets up**

* **Background spinning:** lets actions, TF, and planning-scene updates progress while your code does blocking waits.
* **Sequential milestones:** call `run_milestone_*` methods after starting the executor.
* **Common pitfall:** calling `rclpy.spin(node)` on the main thread will block your sequential code. Use the executor thread instead.

---

### 2) Arm interface (MoveIt 2 wrapper)

Construct the planner/controller wrapper for your arm planning group.

```python
from pymoveit2 import MoveIt2

self.moveit2 = MoveIt2(
    node=self,
    joint_names=["JOINT_1","JOINT_2","JOINT_3","JOINT_4","JOINT_5","JOINT_6"],
    base_link_name="BASE_LINK",
    end_effector_name="EE_LINK",
    group_name="ARM_GROUP",
)
# Optional comfort limits (0.0–1.0)
self.moveit2.max_velocity = 0.5
self.moveit2.max_acceleration = 0.5
# Optional: planner choice (if available)
# self.moveit2.planner_id = "RRTConnectkConfigDefault"
```

**What each field means**

* `joint_names` — **ordered** list in **SRDF joint order**. This order is used when you send joint arrays.
* `base_link_name` — the **planning frame** (often `base_link` or `world`).
* `end_effector_name` — the EE link used for pose queries and IK (e.g., `end_effector_link`).
* `group_name` — the MoveIt **planning group** (e.g., `arm`).

**Gotchas**

* Using the wrong **joint order** will cause nonsense motions or planning failure.
* Frames/group names must exactly match your model; confirm in RViz (MotionPlanning → Groups/Joints) or the SRDF.
* Max velocity/acceleration are **scales** (0–1) applied to the robot’s limits.

---

### 3) Joint-space planning (named states or explicit arrays)

When: moving between known, safe configurations (e.g., `home` → a tucked “retract”).

```python
# Named state
self.moveit2.move_to_configuration("home")
self.moveit2.wait_until_executed()

# Explicit joint array (rad), SRDF order
retract = [J1, J2, J3, J4, J5, J6]
self.moveit2.move_to_configuration(retract)
self.moveit2.wait_until_executed()
```

**What to check**

* **Named targets** exist only if defined in the SRDF; otherwise use explicit arrays.
* For explicit arrays, ensure `len(array) == len(joint_names)` and all values are **within limits**.
* If motion aborts instantly: check for **self-collision**, **limits**, or a misconfigured controller.

---

### 4) Cartesian waypoints (straight-line EE motion)

Core: `get_current_pose()`, `plan_cartesian_path(waypoints) -> (plan, fraction)`, `execute(plan)`.

```python
from copy import deepcopy

start = self.moveit2.get_current_pose()
wps = [deepcopy(start)]

p1 = deepcopy(start); p1.position.x += 0.10; wps.append(p1)   # +10 cm X
p2 = deepcopy(p1);    p2.position.z += 0.05; wps.append(p2)   # +5 cm Z

plan, fraction = self.moveit2.plan_cartesian_path(waypoints=wps)
if fraction > 0.90:
    self.moveit2.execute(plan)
    self.moveit2.wait_until_executed()
else:
    self.get_logger().warn(f"Low fraction={fraction:.2f}; try smaller steps/closer waypoints.")
```

**What the numbers mean**

* `fraction` ∈ \[0, 1] = proportion of your requested path that is **IK-feasible & collision-free**.
* `< 1.0` usually means: waypoints too far apart, EE orientation is difficult, path clips an obstacle, or you’re near a singularity/limit.

**Tips**

* Keep orientation **fixed** at first; add rotations later.
* Smaller translation steps (e.g., 0.02–0.05 m) improve IK success.
* If exposed by your wrapper, reducing interpolation step size can increase `fraction`.

---

### 5) Planning scene (collision objects)

Make the planner aware of obstacles/fixtures.

```python
obj_id = "UNIQUE_ID"
self.moveit2.add_collision_box(
    id=obj_id,
    position=(X, Y, Z),        # meters in FRAME
    quat_xyzw=(qx, qy, qz, qw),
    size=(sx, sy, sz),         # meters
    frame_id="FRAME",          # often your planning frame, e.g., base_link
)
time.sleep(1.0)  # allow scene to propagate
# Optional cleanup:
# self.moveit2.remove_collision_object(obj_id)
```

**What to remember**

* `id` must be **unique** per object (you use it again to update/remove).
* `position` is the **box center** in `frame_id`.
* `size` is the box **dimensions** along its local x/y/z.
* After adding, give the scene a short moment to sync before planning.

**Pitfalls**

* Wrong `frame_id` ⇒ obstacle appears somewhere unexpected (or not at all).
* Making the box too large can block **all** paths; start conservative.

---

### 6) Orientation constraints (optional)

Constrain tool orientation within tolerances during a move.

```python
self.moveit2.set_path_orientation_constraint(
    quat_xyzw=(qx, qy, qz, qw),
    tolerance=(roll_tol, pitch_tol, yaw_tol),  # radians
    parameterization=1,
)
# … issue your constrained move …
# (Remember to clear/relax constraints afterward)
```

**What it enforces**

* Keeps EE orientation near `quat_xyzw` with per-axis **tolerances** (radians).
* Applies to **subsequent** plans until changed/cleared.

**Tips**

* Start with wide tolerances (e.g., \~0.35 rad ≈ 20°) to avoid over-constraining.
* Constrained planning can reduce success rate and increase planning time.

---

### 7) Gripper interface (ROS 2 Action–backed)

High-level open/close with feedback and result (e.g., `control_msgs/GripperCommand`).

```python
from pymoveit2.gripper_interface import GripperInterface

self.gripper = GripperInterface(
    node=self,
    gripper_joint_names=[PRIMARY_ACTUATED_JOINT],
    open_gripper_joint_positions=[OPEN_TARGET],
    closed_gripper_joint_positions=[CLOSE_TARGET],
    gripper_group_name="GRIPPER_GROUP",
    gripper_command_action_name="/PATH/TO/gripper_cmd",
)

self.gripper.open();  self.gripper.wait_until_executed()
self.gripper.close(); self.gripper.wait_until_executed()
```

**What to supply**

* **Primary actuated joint** only (mimic joints will follow).
* **Open/close targets** must match your sim/driver ranges.
* **Action name** must match the controller’s action server (discover with `ros2 action list`).

**If nothing happens**

* Check the action server exists (`ros2 action info …`), and the gripper controller is **active** (`ros2 control list_controllers`).

---

### 8) Minimal API signatures

Below is what each call expects/returns and the **units/frames** it assumes. When in doubt, pull names from your SRDF/RViz and treat all linear distances as **meters** and angles as **radians**. Quaternions are **(x, y, z, w)**.

---

#### **Joint goals**

**`move_to_configuration(target: str | list[float]) -> None`**

* **`target` (str):** A **named state** defined in your SRDF (e.g., `"home"`). Check RViz → MotionPlanning → **Goal State** dropdown or inspect the SRDF.
* **`target` (list\[float]):** A full joint vector in **SRDF joint order** (e.g., 6 angles for a 6-DOF arm). Must respect joint limits.
* **What it does:** Plans **and starts** execution of a collision-checked trajectory to the goal. It does **not** block; pair with `wait_until_executed()`.
* **Common pitfalls:** Wrong joint order; values outside limits; self-collision along the path; named state doesn’t exist in your model.

**`wait_until_executed() -> None`**

* **What it does:** **Blocks** until the most recent arm/gripper action finishes (success/abort).
* **Use when:** You want sequential behavior (e.g., “move, then plan again” or “open, then close”).

---

#### **Cartesian**

**`get_current_pose() -> geometry_msgs.msg.Pose`**

* **Returns:** The end-effector **pose in the planning frame** (often `base_link` or `world`).
* **Tip:** `deepcopy()` this pose before modifying; Pose objects are mutable.

**`plan_cartesian_path(waypoints: list[Pose]) -> (plan, fraction: float)`**

* **`waypoints`:** List of **Pose** in the **planning frame**. The **first** waypoint should be the current pose. Keep orientation fixed at first.
* **`plan`:** A MoveIt trajectory you can pass to `execute()`.
* **`fraction`:** Portion \[0–1] of the path that is IK-feasible and collision-free (e.g., 0.92 = 92% of the requested path).
* **Does not execute:** You must call `execute(plan)` yourself.
* **Why `< 1.0`?** IK failure at some waypoint(s), step too large, collisions, singular/near-limit poses.

**`execute(plan) -> None`**

* **What it does:** Sends a previously computed `plan` to the controller. **Non-blocking**; follow with `wait_until_executed()`.
* **Pitfalls:** Controller inactive/mismatched; stale plan after environment changed.

---

#### **Scene**

**`add_collision_box(id: str, position: (x,y,z), quat_xyzw: (x,y,z,w), size: (sx,sy,sz), frame_id: str) -> None`**

* **`id`:** **Unique** name for this object (used to update/remove later).
* **`position`:** Box center in **meters**, expressed in `frame_id`.
* **`quat_xyzw`:** Box orientation as a normalized quaternion.
* **`size`:** Box dimensions in meters along its local x/y/z.
* **`frame_id`:** TF frame you’re expressing `position/orientation` in (often the **planning frame** like `base_link` or `world`).
* **Effect:** Publishes to the **Planning Scene**; give RViz/MoveIt a short moment to sync (e.g., `time.sleep(1.0)`).

**`remove_collision_object(id: str) -> None`** *(optional)*

* **What it does:** Removes the object with this `id` from the planning scene.

---

#### **Constraints**

**`set_path_orientation_constraint(quat_xyzw: tuple[4], tolerance: tuple[3], parameterization: int) -> None`**

* **`quat_xyzw`:** Desired **global** end-effector orientation (in the planning frame).
* **`tolerance`:** `(roll_tol, pitch_tol, yaw_tol)` **radians** allowed around that orientation. Start wide (e.g., 0.35 ≈ 20°).
* **`parameterization`:** Implementation-specific enum (your build often uses `1`).
* **Behavior:** Applies to **subsequent** plans until changed/cleared. Tight tolerances reduce planning success.
* **Clearing:** If your wrapper lacks an explicit “clear” call, relax tolerances (large values) or re-initialize as needed.

---

#### **Gripper**

**`open() -> None`, `close() -> None`**

* **What they do:** Send a **ROS 2 Action** goal (e.g., `GripperCommand`) to move the gripper to the configured **open/closed** positions. **Non-blocking**; follow with `wait_until_executed()`.
* **Back end:** Requires a running gripper **action server** (discover via `ros2 action list`).
* **Mimic joints:** Many grippers mirror motion; you command only the **primary** joint.

**`wait_until_executed() -> None`**

* **What it does:** Blocks until the gripper action reports result (success/abort).
* **Tip:** Add a short `time.sleep(1.0)` between open/close when you want a visible pause for screenshots.

---

##### Quick sanity for **names/frames** these signatures reference

* **Joint order / named states / groups:** SRDF (get from `/move_group`’s `robot_description_semantic`), or RViz → MotionPlanning.
* **Planning frame & EE link:** RViz **Fixed Frame**, TF tree, or your MoveIt config.
* **Gripper action name:** `ros2 action list | grep -i gripper` (then `ros2 action info <name>`).
* **Controllers:** `ros2 control list_controllers` (should show active trajectory & gripper controllers).


---

### 9) Common pitfalls & fast checks

* **Nothing executes:** `ros2 control list_controllers` → trajectory/gripper controller **active?**
* **Wrong names:** verify **group**, **frames**, **joint order** from SRDF/RViz.
* **Cartesian fraction low:** smaller waypoint steps, keep orientation fixed, ensure waypoints are not **inside obstacles**.
* **Scene not visible:** enable PlanningScene/Collision in RViz; confirm `frame_id`; wait \~1 s after adding objects.

---