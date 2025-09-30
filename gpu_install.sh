#!/usr/bin/env bash
# enable_gpu_docker.sh — Set up NVIDIA Container Toolkit on Ubuntu (24.04-friendly)
# Safe to re-run; exits on any error.

set -euo pipefail

say() { printf "\n\033[1;36m%s\033[0m\n" "$*"; }
err() { printf "\n\033[1;31m%s\033[0m\n" "$*" >&2; }

require() {
  if ! command -v "$1" >/dev/null 2>&1; then
    err "Missing required command: $1"
    exit 1
  fi
}

say "1) Preflight checks"
require curl
require sudo
require docker
if ! groups "$USER" | grep -q docker; then
  err "You are not in the 'docker' group. Run: sudo usermod -aG docker $USER && newgrp docker"
fi

say "2) Clean any broken NVIDIA repo entries"
sudo rm -f /etc/apt/sources.list.d/nvidia-container-toolkit.list \
            /etc/apt/sources.list.d/nvidia-container-toolkit*.list \
            /etc/apt/keyrings/nvidia-container-toolkit.asc \
            /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg || true

say "3) Add NVIDIA repo key + list (generic deb channel)"
sudo install -d -m 0755 /etc/apt/keyrings
sudo wget -qO /etc/apt/keyrings/nvidia-container-toolkit.asc \
  https://nvidia.github.io/libnvidia-container/gpgkey

# Use the generic deb/amd64 repo to avoid distro string issues
echo "deb [signed-by=/etc/apt/keyrings/nvidia-container-toolkit.asc] \
https://nvidia.github.io/libnvidia-container/stable/deb/amd64 /" \
| sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list >/dev/null

say "4) apt update + install toolkit"
sudo apt-get update -y
sudo apt-get install -y \
  libnvidia-container1 libnvidia-container-tools \
  nvidia-container-toolkit-base nvidia-container-toolkit || {
    err "apt couldn’t find NVIDIA toolkit packages. Check the repo list above and your network."
    exit 1
  }

say "5) Configure Docker to use NVIDIA runtime"
if command -v nvidia-ctk >/dev/null 2>&1; then
  sudo nvidia-ctk runtime configure --runtime=docker
else
  err "nvidia-ctk not found (unexpected). Writing a minimal /etc/docker/daemon.json fallback."
  sudo tee /etc/docker/daemon.json >/dev/null <<'JSON'
{
  "runtimes": {
    "nvidia": {
      "path": "nvidia-container-runtime",
      "runtimeArgs": []
    }
  },
  "default-runtime": "nvidia"
}
JSON
fi

say "6) Restart Docker"
sudo systemctl restart docker

say "7) Sanity checks"
docker info | grep -i -E 'runtimes|default-runtime' || true

if command -v nvidia-smi >/dev/null 2>&1; then
  say "Host GPU present. Testing inside a container..."
  docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi || {
    err "Container couldn’t access the GPU. If on a VM, verify the GPU is attached and drivers are loaded."
    exit 1
  }
  say "Success: container can see the GPU."
else
  err "Host nvidia-smi not found. You likely don’t have a visible GPU on this VM."
  err "You can still run Docker without --gpus. For RViz/Gazebo software rendering, export LIBGL_ALWAYS_SOFTWARE=1."
fi

say "Done."
