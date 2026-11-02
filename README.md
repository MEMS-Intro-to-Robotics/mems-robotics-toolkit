# MEMS Robotics Toolkit

This repository hosts the shared **setup scripts** and **prebuilt Docker images** used across Duke's **Intro to Robotics** (ECE 383 / ME 555). It's the "base camp" for your dev environment so every student starts from the same, working stack.

**Who this is for**

* Students working on labs in a Duke VCM (FastX) session.
* TAs/instructors maintaining the standard images and starter assets.

---

## Quick Start

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

> Switch the tag to the appropriate platform as documented in the lab manuals.

**Updating later:** pull again with the same tag to get the latest toolchain.

---

## Repository Contents

```
mems-robotics-toolkit/
├── guides/                  # Documentation and reference guides
├── lab06_files/             # Lab 6: Pick & Place starter code
├── lab07_files/             # Lab 7: 3D Goal Controller starter code
├── dockerfiles/             # Dockerfile sources for course images
├── vm_setup.sh              # VM environment setup script
├── move_docker_to_home.sh   # Move Docker storage from the 25 GB root volume to /home
└── gpu_install.sh           # NVIDIA GPU setup (optional)
```

### Docker Images

| Image Tag | Description |
|-----------|-------------|
| `...:base-jazzy-latest` | Generic ROS 2 Jazzy + dev utilities |
| `...:kinova-jazzy-latest` | Adds Kinova + MoveIt 2 simulation stack |

---

## Guides

Start with the Quick Reference, then explore topic-specific guides as needed.

| Guide | Description |
|-------|-------------|
| [Quick Reference](guides/quick_reference.md) | Linux, Git, Docker, ROS 2, MoveIt basics - **start here** |
| [pymoveit2 API Guide](guides/pymoveit2_api_guide.md) | Core MoveIt2 Python API reference |
| [Kinova Gen3 Lite Guide](guides/kinova_gen3_lite_moveit2_guide.md) | Robot-specific setup and configuration |
| [Velocity Controlled Joint Motion](guides/velocity_controlled_joint_motion_guide.md) | Direct joint velocity control |
| [Multi-Robot Coordination](guides/multi_robot_coordination_guide.md) | Coordinating multiple robotic systems |
| [RGB-D Camera Integration](guides/rgbd_camera_integration_guide.md) | Depth camera setup and point clouds |

See [guides/README.md](guides/README.md) for suggested reading order.

---

## Lab Starter Code

| Lab | Description | Link |
|-----|-------------|------|
| Lab 6 | Pick & Place with Kinova Gen3 Lite | [lab06_files/](lab06_files/) |
| Lab 7 | 3D PID Goal Controller | [lab07_files/](lab07_files/) |

Each lab folder contains a README with quick start instructions.

---

## Good to Know

* Don't `apt install` inside containers unless the lab says so; the images already include dependencies.
* Keep your **personal lab repo** separate under `~/workspaces/<netid>_robotics_fall2025`.
* If GUIs don't show up from the container, re-run `xhost +local:docker` on the VM.

---

## Getting Help

1. First: see the [Quick Reference](guides/quick_reference.md).
2. Then: check your lab PDF, and course Ed/Teams for known issues.
3. Still stuck? Open an issue on this repo with your image tag, commands, and logs.
