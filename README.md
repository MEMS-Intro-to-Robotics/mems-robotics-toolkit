# MEMS Robotics Toolkit

This repository hosts shared setup scripts and prebuilt Docker images for the Duke **Intro to Robotics** course (ECE 383 / ME 555).

## Contents

- `vm_setup.sh` — installs core utilities (Docker, VS Code, Git) inside the course VM.
- **Container Registry** — prebuilt Docker images used in labs:
  - `jazzy-base` — base ROS 2 Jazzy image
  - `kinova-sim` — Kinova Gen3 Lite simulation
  - `tb4-sim` — TurtleBot 4 simulation
  - `ur5e-sim` — UR5e simulation

## Usage


```bash
docker pull gitlab-registry.oit.duke.edu/introtorobotics/mems-robotics-toolkit:jazzy-base-latest
