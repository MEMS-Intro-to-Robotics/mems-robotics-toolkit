#!/bin/bash
# =============================================================================
# Intro to Robotics 2025 — VM Environment Setup Script
# Duke University, Thomas Lord Department of Mechanical Engineering & Materials Science
# Author: Evan Kusa
# =============================================================================
# This script installs essential utilities for the course VM environment,
# plus FastX 4 Server + XFCE with headless license activation.
# Usage (recommended):
#   FASTX_ACTIVATION_KEY="####-####-####-####" bash setup.sh
# =============================================================================

set -e

# -----------------------------
# Helper Functions
# -----------------------------
function output_message {
    echo -e "\n===== $1 =====\n"
}

function wait_for_dpkg_lock {
    while sudo fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1; do
        output_message "Waiting for dpkg lock..."
        sleep 5
    done
}

# -----------------------------
# Locale Setup
# -----------------------------
output_message "Setting locale..."
wait_for_dpkg_lock
sudo apt update -y
sudo apt install -y locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

# -----------------------------
# Base Development Utilities
# -----------------------------
output_message "Installing base development utilities..."
wait_for_dpkg_lock
sudo apt install -y \
    curl wget git ssh \
    build-essential cmake \
    python3 python3-pip \
    net-tools htop tmux terminator \
    software-properties-common apt-transport-https ca-certificates gnupg lsb-release

# -----------------------------
# Docker Installation
# -----------------------------
output_message "Installing Docker..."
wait_for_dpkg_lock
sudo apt install -y docker.io
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER" || true

# -----------------------------
# Visual Studio Code
# -----------------------------
output_message "Installing Visual Studio Code..."
wait_for_dpkg_lock
wget -q https://packages.microsoft.com/keys/microsoft.asc -O- | sudo gpg --dearmor -o /usr/share/keyrings/packages.microsoft.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/packages.microsoft.gpg] https://packages.microsoft.com/repos/vscode stable main" \
  | sudo tee /etc/apt/sources.list.d/vscode.list > /dev/null
sudo apt update -y
sudo apt install -y code

# -----------------------------
# VS Code Extensions (ROS 2 dev)
# -----------------------------
output_message "Installing VS Code extensions..."
if command -v code >/dev/null 2>&1; then
  # Core language support
  code --install-extension ms-python.python --force
  code --install-extension ms-vscode.cpptools --force

  # ROS 2 tooling
  code --install-extension ms-vscode.cmake-tools --force
  code --install-extension DotJoshJohnson.xml --force
  code --install-extension redhat.vscode-yaml --force

  # Containers / remote dev
  code --install-extension ms-vscode-remote.remote-containers --force
  code --install-extension ms-azuretools.vscode-docker --force

  # Show what’s installed (optional)
  code --list-extensions || true
else
  output_message "VS Code CLI 'code' not found in PATH; skipping extension installs."
fi

# -----------------------------
# Command Line Practice Files
# -----------------------------
output_message "Creating sample files for command line practice..."
mkdir -p ~/cli_practice && cd ~/cli_practice
echo "This is a sample text file for command line practice." > file.txt
echo -e '#!/bin/bash\necho "This is a simulated program output."' > myprog
chmod +x myprog
touch sample1.txt sample2.txt
cd ~

# -----------------------------
# Setup FastX Repository
# -----------------------------
output_message "Setting up FastX 4 repository..."
wait_for_dpkg_lock
wget -q https://www.starnet.com/files/private/setup-starnet-repo.sh -O /tmp/setup-starnet-repo.sh
sudo bash /tmp/setup-starnet-repo.sh
rm -f /tmp/setup-starnet-repo.sh

# -----------------------------
# Remote Desktop (FastX 4 Server + XFCE)
# -----------------------------
output_message "Installing XFCE Desktop (lightweight), web browser, and FastX 4 Server..."
wait_for_dpkg_lock
sudo apt update -y
sudo DEBIAN_FRONTEND=noninteractive apt install -y \
  xfce4 xfce4-terminal xfce4-goodies

# FastX server and activation prerequisites
wait_for_dpkg_lock
sudo DEBIAN_FRONTEND=noninteractive apt install -y \
  fastx4-server \
  libnet-ssleay-perl libio-socket-ssl-perl ca-certificates

# Prepare FastX directories/ownership
sudo mkdir -p /var/fastx/license
sudo chown -R fastx:fastx /var/fastx

# Note: License activation must now be done manually.
echo "===================================================================="
echo "⚠️  FastX installed but NOT activated."
echo "Run the following command manually to activate your license:"
echo "    sudo -u fastx /usr/lib/fastx/4/install/activate"
echo "Then enter your license key when prompted."
echo "===================================================================="

# Enable/start services (names may vary by build — both attempted)
sudo systemctl enable --now fastx4-rlm 2>/dev/null || true
sudo systemctl enable --now fastx4 2>/dev/null || true

# Clear any stale XFCE session to avoid odd multi-panel 'failsafe' layout
rm -rf "${HOME}/.cache/sessions" || true

# Quick diagnostics (non-fatal)
output_message "FastX quick checks (non-fatal)..."
sudo journalctl -u fastx4-rlm -n 5 --no-pager || true
if command -v ss >/dev/null 2>&1; then
  ss -tlnp | grep 3300 || true
else
  netstat -tlnp | grep 3300 || true
fi

#!/bin/bash
set -e

# ================================
# Install basic utilities
# ================================
sudo apt update
sudo apt install -y \
  nano vim tree zip unzip p7zip-full \
  dnsutils iputils-ping traceroute \
  evince xclip gnome-system-monitor \
  software-properties-common apt-transport-https

# ================================
# Configure Firefox (non-snap)
# ================================
# Remove any snap version
sudo snap remove firefox || true

# Add Mozilla PPA
sudo add-apt-repository -y ppa:mozillateam/ppa

# Create apt pinning rules to prefer PPA .deb over snap
sudo tee /etc/apt/preferences.d/firefox-no-snap > /dev/null <<EOF
Package: firefox*
Pin: release o=Ubuntu*
Pin-Priority: -1
EOF

sudo tee /etc/apt/preferences.d/mozillateam-firefox > /dev/null <<EOF
Package: firefox*
Pin: release o=LP-PPA-mozillateam
Pin-Priority: 501
EOF

# Update and install Firefox
sudo apt update
sudo apt install -y firefox



# -----------------------------
# Final Cleanup
# -----------------------------
output_message "Performing cleanup..."
wait_for_dpkg_lock
sudo apt autoremove -y
sudo apt clean

output_message "Setup complete!"

echo "Docker note: log out/in or reboot VM for docker group to take effect."
