#!/usr/bin/env bash
# =============================================================================
# Intro to Robotics 2025 — VM Environment Setup (All-in-One)
# Duke University, Thomas Lord Department of Mechanical Engineering & Materials Science
# Author: Evan Kusa
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
if command -v snap >/dev/null 2>&1; then
  sudo snap remove firefox || true
fi
if dpkg -l | grep -q "^ii\s\+firefox\s"; then
  wait_for_dpkg_lock
  sudo apt-get purge -y firefox || true
fi

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
# Visual Studio Code & Extensions
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
  
  # Jupyter Support
  code --install-extension ms-toolsai.jupyter --force || true
  code --install-extension ms-toolsai.jupyter-keymap --force || true
  code --install-extension ms-toolsai.jupyter-renderers --force || true

  # ROS 2 tooling
  code --install-extension ms-vscode.cmake-tools --force || true
  code --install-extension DotJoshJohnson.xml --force || true
  code --install-extension redhat.vscode-yaml --force || true
  
  # Containers / remote dev
  code --install-extension ms-vscode-remote.remote-containers --force || true
  code --install-extension ms-azuretools.vscode-docker --force || true
  
  # Tunnels for Headless access
  code --install-extension ms-vscode.remote-server --force || true
else
  warn "VS Code CLI 'code' not found; skipping extension installs."
fi

# -----------------------------
# GitHub CLI
# -----------------------------
say "Installing GitHub CLI (gh)"
wait_for_dpkg_lock
sudo install -d -m 0755 /etc/apt/keyrings
wget -qO- https://cli.github.com/packages/githubcli-archive-keyring.gpg \
  | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg >/dev/null
sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
  | sudo tee /etc/apt/sources.list.d/github-cli.list >/dev/null
wait_for_dpkg_lock
sudo apt-get update -y
sudo apt-get install -y gh

# -----------------------------
# Python test tooling
# -----------------------------
# Ubuntu 24.04 marks the system Python as externally managed (PEP 668), so
# "python3 -m pip install pytest" fails without a virtual environment. The apt
# package gives students a working "pytest" command with no extra steps.
say "Installing Python test tooling"
wait_for_dpkg_lock
sudo apt-get install -y python3-pytest
if ! command -v pytest >/dev/null 2>&1; then
  if command -v pytest-3 >/dev/null 2>&1; then
    sudo ln -sf "$(command -v pytest-3)" /usr/local/bin/pytest
  else
    warn "python3-pytest installed but no pytest command is on PATH."
  fi
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

# -----------------------------
# FastX 4 (Legacy / Backup Access)
# -----------------------------
say "Setting up FastX 4 repository"
wait_for_dpkg_lock
wget -q https://www.starnet.com/files/private/setup-starnet-repo.sh -O /tmp/setup-starnet-repo.sh
sudo bash /tmp/setup-starnet-repo.sh
rm -f /tmp/setup-starnet-repo.sh

say "Installing XFCE Desktop + FastX 4 Server"
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  xfce4 xfce4-terminal xfce4-goodies fastx4-server \
  libnet-ssleay-perl libio-socket-ssl-perl ca-certificates

# Prepare FastX directories/ownership
sudo mkdir -p /var/fastx/license
sudo chown -R fastx:fastx /var/fastx || true
rm -rf "${HOME}/.cache/sessions" || true

# Activate the FastX license without prompting. The activate helper has no
# documented command-line flags, so the key and seat count are supplied on
# stdin. Activation is verified by checking that a license file was written.
say "Activating FastX 4"
if [ -n "${FASTX_ACTIVATION_KEY:-}" ]; then
  if [ -x /usr/lib/fastx/4/install/activate ]; then
    printf '%s\n%s\n' "${FASTX_ACTIVATION_KEY}" "${FASTX_SEATS:-1}" \
      | sudo -u fastx /usr/lib/fastx/4/install/activate || \
      warn "FastX activate helper returned a non-zero status."
  else
    warn "FastX activate helper not found at /usr/lib/fastx/4/install/activate."
  fi
  if [ -n "$(sudo ls -A /var/fastx/license 2>/dev/null)" ]; then
    say "FastX license installed"
  else
    warn "No license file in /var/fastx/license. Activate manually with:"
    warn "  sudo -u fastx /usr/lib/fastx/4/install/activate"
    warn "  key: ${FASTX_ACTIVATION_KEY}   seats: ${FASTX_SEATS:-1}"
  fi
else
  warn "FASTX_ACTIVATION_KEY is not set, so FastX was not activated."
  warn "Re-run with FASTX_ACTIVATION_KEY=\"<key>\" ./vm_setup.sh, or activate"
  warn "manually with: sudo -u fastx /usr/lib/fastx/4/install/activate"
fi

# -----------------------------
# NVIDIA Container Toolkit
# -----------------------------
say "Installing NVIDIA Container Toolkit (optional)"
if ! command -v docker >/dev/null 2>&1; then
  warn "Docker not found in PATH (unexpected). Skipping NVIDIA toolkit configuration."
else
  # Clean old and install new
  sudo rm -f /etc/apt/sources.list.d/nvidia-container-toolkit.list \
              /etc/apt/keyrings/nvidia-container-toolkit.asc || true

  sudo install -d -m 0755 /etc/apt/keyrings
  sudo wget -qO /etc/apt/keyrings/nvidia-container-toolkit.asc \
    https://nvidia.github.io/libnvidia-container/gpgkey

  echo "deb [signed-by=/etc/apt/keyrings/nvidia-container-toolkit.asc] https://nvidia.github.io/libnvidia-container/stable/deb/amd64 /" \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list >/dev/null

  if sudo apt-get update -y && sudo apt-get install -y nvidia-container-toolkit; then
    say "Configuring Docker to use NVIDIA runtime"
    if command -v nvidia-ctk >/dev/null 2>&1; then
      sudo nvidia-ctk runtime configure --runtime=docker || warn "nvidia-ctk configure failed"
      sudo systemctl restart docker
    fi
  else
    warn "NVIDIA toolkit packages could not be installed. Skipping GPU setup."
  fi
fi

# -----------------------------
# Headless Mode Setup
# -----------------------------
say "Setting up Headless Access Options"
# This enables the 'code tunnel' service. Students can run 'code tunnel' 
# to link this VM to their GitHub account, allowing them to access this VM
# from https://vscode.dev or their local VS Code Desktop WITHOUT FastX.
if command -v code >/dev/null 2>&1; then
  echo "VS Code CLI installed. To enable headless access:"
  echo "  Run: 'code tunnel'"
  echo "  This allows you to connect to this VM from your laptop's VS Code."
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
