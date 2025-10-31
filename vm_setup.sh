#!/usr/bin/env bash
# =============================================================================
# Intro to Robotics 2025 — VM Environment Setup (All-in-One)
# Duke University, Thomas Lord Department of Mechanical Engineering & Materials Science
# Author: Evan Kusa
# =============================================================================
# What this does (one shot):
# - Locale + base dev utils
# - Docker (apt docker.io) + user in docker group
# - (Optional) NVIDIA Container Toolkit for GPU-accelerated Docker
# - Firefox (non-snap via Mozilla PPA, with pinning)
# - VS Code + core extensions
# - Handy desktop/CLI utilities
# - FastX 4 repo + XFCE + FastX 4 Server (prints license activation instructions)
# - Creates some CLI practice files
#
# Usage (recommended):
#   FASTX_ACTIVATION_KEY="####-####-####-####" bash setup_all.sh   # (key is NOT auto-used; for your reference)
#
# Notes:
# - You must log out/in after this so your ‘docker’ group membership takes effect.
# - GPU section installs NVIDIA Container Toolkit and configures Docker; it gracefully continues if unavailable.
# =============================================================================

set -euo pipefail

# -----------------------------
# Helpers
# -----------------------------
say() { printf "\n\033[1;36m===== %s =====\033[0m\n\n" "$*"; }
warn() { printf "\n\033[1;33m[WARN]\033[0m %s\n" "$*" >&2; }
err() { printf "\n\033[1;31m[ERROR]\033[0m %s\n" "$*" >&2; }
require() { command -v "$1" >/dev/null 2>&1 || { err "Missing required command: $1"; exit 1; }; }

wait_for_dpkg_lock() {
  while sudo fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1; do
    say "Waiting for dpkg lock..."
    sleep 5
  done
}

# Make sure sudo is ready
sudo -v || true

# -----------------------------
# Locale
# -----------------------------
say "Setting locale"
wait_for_dpkg_lock
sudo apt-get update -y
sudo apt-get install -y locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

# -----------------------------
# Base development utilities
# -----------------------------
say "Installing base development utilities"
wait_for_dpkg_lock
sudo apt-get install -y \
  curl wget git ssh \
  build-essential cmake ninja-build \
  python3 python3-pip python3-venv \
  net-tools htop tmux terminator \
  software-properties-common apt-transport-https ca-certificates gnupg lsb-release

# Additional QoL & troubleshooting tools
wait_for_dpkg_lock
sudo apt-get install -y \
  nano vim tree zip unzip p7zip-full \
  dnsutils iputils-ping traceroute \
  evince xclip gnome-system-monitor \
  ncdu bat fd-find \
  gnome-tweaks gparted meld vlc fonts-firacode

# -----------------------------
# Docker
# -----------------------------
say "Installing Docker (docker.io)"
wait_for_dpkg_lock
sudo apt-get install -y docker.io
sudo systemctl enable --now docker
# Add current user to docker group (non-fatal if already added)
sudo usermod -aG docker "$USER" || true

# -----------------------------
# Firefox (non-snap via PPA, with pinning)
# -----------------------------
say "Installing Firefox (non-snap) via Mozilla PPA"
# Remove snap Firefox if present (ignore failures)
if command -v snap >/dev/null 2>&1; then
  sudo snap remove firefox || true
fi
# Purge transitional apt firefox if present (ignore failures)
if dpkg -l | grep -q "^ii\s\+firefox\s"; then
  wait_for_dpkg_lock
  sudo apt-get purge -y firefox || true
fi

# Add PPA & pin rules
wait_for_dpkg_lock
sudo add-apt-repository -y ppa:mozillateam/ppa
sudo tee /etc/apt/preferences.d/firefox-no-snap >/dev/null <<'EOF'
Package: firefox*
Pin: release o=Ubuntu*
Pin-Priority: -1
EOF
sudo tee /etc/apt/preferences.d/mozillateam-firefox >/dev/null <<'EOF'
Package: firefox*
Pin: release o=LP-PPA-mozillateam
Pin-Priority: 501
EOF

wait_for_dpkg_lock
sudo apt-get update -y
sudo apt-get install -y firefox

# -----------------------------
# Visual Studio Code
# -----------------------------
say "Installing Visual Studio Code"
wait_for_dpkg_lock
wget -q https://packages.microsoft.com/keys/microsoft.asc -O- | sudo gpg --dearmor -o /usr/share/keyrings/packages.microsoft.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/packages.microsoft.gpg] https://packages.microsoft.com/repos/vscode stable main" \
  | sudo tee /etc/apt/sources.list.d/vscode.list >/dev/null
wait_for_dpkg_lock
sudo apt-get update -y
sudo apt-get install -y code

say "Installing recommended VS Code extensions"
if command -v code >/dev/null 2>&1; then
  # Core language support
  code --install-extension ms-python.python --force || true
  code --install-extension ms-vscode.cpptools --force || true
  # ROS 2 tooling
  code --install-extension ms-vscode.cmake-tools --force || true
  code --install-extension DotJoshJohnson.xml --force || true
  code --install-extension redhat.vscode-yaml --force || true
  # Containers / remote dev
  code --install-extension ms-vscode-remote.remote-containers --force || true
  code --install-extension ms-azuretools.vscode-docker --force || true
  code --list-extensions || true
else
  warn "VS Code CLI 'code' not found; skipping extension installs."
fi

# -----------------------------
# Command-line practice files
# -----------------------------
say "Creating sample files for command line practice"
mkdir -p "${HOME}/cli_practice"
cat > "${HOME}/cli_practice/myprog" <<'SH'
#!/usr/bin/env bash
echo "This is a simulated program output."
SH
chmod +x "${HOME}/cli_practice/myprog"
echo "This is a sample text file for command line practice." > "${HOME}/cli_practice/file.txt"
touch "${HOME}/cli_practice/sample1.txt" "${HOME}/cli_practice/sample2.txt"

# -----------------------------
# FastX 4 repository + XFCE + FastX Server
# -----------------------------
say "Setting up FastX 4 repository"
wait_for_dpkg_lock
wget -q https://www.starnet.com/files/private/setup-starnet-repo.sh -O /tmp/setup-starnet-repo.sh
sudo bash /tmp/setup-starnet-repo.sh
rm -f /tmp/setup-starnet-repo.sh

say "Installing XFCE Desktop + FastX 4 Server"
wait_for_dpkg_lock
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  xfce4 xfce4-terminal xfce4-goodies

wait_for_dpkg_lock
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  fastx4-server \
  libnet-ssleay-perl libio-socket-ssl-perl ca-certificates

# Prepare FastX directories/ownership
sudo mkdir -p /var/fastx/license
sudo chown -R fastx:fastx /var/fastx || true

# Enable/start services if present
sudo systemctl enable --now fastx4-rlm 2>/dev/null || true
sudo systemctl enable --now fastx4 2>/dev/null || true

# Clear any stale XFCE session to avoid odd multi-panel layouts
rm -rf "${HOME}/.cache/sessions" || true

say "FastX quick checks (non-fatal)"
sudo journalctl -u fastx4-rlm -n 5 --no-pager || true
if command -v ss >/dev/null 2>&1; then
  ss -tlnp | grep 3300 || true
else
  netstat -tlnp | grep 3300 || true
fi

echo "===================================================================="
echo "⚠️  FastX installed but NOT activated."
echo "Run the following command to activate your license (interactive):"
echo "    sudo -u fastx /usr/lib/fastx/4/install/activate"
echo "Then enter your license key when prompted."
echo "===================================================================="

# -----------------------------
# NVIDIA Container Toolkit (GPU for Docker) — optional, continues on failure
# -----------------------------
say "Installing NVIDIA Container Toolkit (optional)"
require curl || true
if ! command -v docker >/dev/null 2>&1; then
  warn "Docker not found in PATH (unexpected). Skipping NVIDIA toolkit configuration."
else
  # Clean any old entries
  sudo rm -f /etc/apt/sources.list.d/nvidia-container-toolkit.list \
              /etc/apt/sources.list.d/nvidia-container-toolkit*.list \
              /etc/apt/keyrings/nvidia-container-toolkit.asc \
              /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg || true

  # Add repo key + generic deb channel
  sudo install -d -m 0755 /etc/apt/keyrings
  sudo wget -qO /etc/apt/keyrings/nvidia-container-toolkit.asc \
    https://nvidia.github.io/libnvidia-container/gpgkey

  echo "deb [signed-by=/etc/apt/keyrings/nvidia-container-toolkit.asc] https://nvidia.github.io/libnvidia-container/stable/deb/amd64 /" \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list >/dev/null

  # Install toolkit (do not fail the whole script)
  if sudo apt-get update -y && sudo apt-get install -y \
      libnvidia-container1 libnvidia-container-tools \
      nvidia-container-toolkit-base nvidia-container-toolkit; then
    say "Configuring Docker to use NVIDIA runtime"
    if command -v nvidia-ctk >/dev/null 2>&1; then
      sudo nvidia-ctk runtime configure --runtime=docker || warn "nvidia-ctk configure failed"
    else
      warn "nvidia-ctk not found; writing minimal /etc/docker/daemon.json fallback"
      sudo tee /etc/docker/daemon.json >/dev/null <<'JSON'
{
  "runtimes": {
    "nvidia": { "path": "nvidia-container-runtime", "runtimeArgs": [] }
  },
  "default-runtime": "nvidia"
}
JSON
    fi
    sudo systemctl restart docker || warn "Failed to restart docker"
    # Sanity check if host GPU present
    if command -v nvidia-smi >/dev/null 2>&1; then
      say "Testing GPU visibility inside a container"
      if docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi; then
        say "Success: container can see the GPU."
      else
        warn "Container could not access the GPU. If this is a VM, ensure a GPU is attached and drivers loaded."
      fi
    else
      warn "Host 'nvidia-smi' not found. Likely no visible GPU. You can still run Docker without --gpus."
      warn "If you hit OpenGL issues in RViz/Gazebo inside containers, try:  export LIBGL_ALWAYS_SOFTWARE=1"
    fi
  else
    warn "NVIDIA toolkit packages could not be installed. Skipping GPU setup."
  fi
fi

# -----------------------------
# Cleanup
# -----------------------------
say "Performing apt cleanup"
wait_for_dpkg_lock
sudo apt-get autoremove -y
sudo apt-get clean

say "Setup complete!"
echo
echo "Docker note: log out/in (or reboot) so your new 'docker' group membership applies."
echo "If using GUI apps from containers: run 'xhost +local:docker' in your VM session first."
