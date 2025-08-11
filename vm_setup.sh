#!/bin/bash
# =============================================================================
# Intro to Robotics 2025 — VM Environment Setup Script
# Duke University, Thomas Lord Department of Mechanical Engineering & Materials Science
# Author: Evan Kusa
# =============================================================================
# This script installs essential utilities for the course VM environment.
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
sudo apt update
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
wget -q https://packages.microsoft.com/keys/microsoft.asc -O- | sudo gpg --dearmor -o /usr/share/keyrings/packages.microsoft.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/packages.microsoft.gpg] https://packages.microsoft.com/repos/vscode stable main" \
  | sudo tee /etc/apt/sources.list.d/vscode.list > /dev/null
sudo apt update
sudo apt install -y code

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
# Final Cleanup
# -----------------------------
output_message "Performing cleanup..."
sudo apt autoremove -y
sudo apt clean

output_message "Setup complete! Please restart your VM for Docker group changes to take effect."
