#!/bin/bash
set -e

echo "===== Utilities Script ====="

# -----------------------------
# Remove snap Firefox if present
# -----------------------------
if snap list | grep -q firefox; then
  sudo snap remove firefox
fi

# Remove apt transitional snap package if present
if dpkg -l | grep -q "firefox"; then
  sudo apt purge -y firefox
fi

# -----------------------------
# Add Mozilla PPA and pin rules
# -----------------------------
sudo add-apt-repository -y ppa:mozillateam/ppa
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

# -----------------------------
# Update + install Firefox (deb)
# -----------------------------
sudo apt update
sudo apt install -y firefox

# -----------------------------
# Core utilities
# -----------------------------
sudo apt install -y \
  nano vim tree zip unzip p7zip-full \
  dnsutils iputils-ping traceroute \
  evince xclip gnome-system-monitor \
  git build-essential cmake ninja-build \
  python3-venv python3-pip

# -----------------------------
# File management / navigation
# -----------------------------
sudo apt install -y \
  htop ncdu bat fd-find

# -----------------------------
# Networking / troubleshooting
# -----------------------------
sudo apt install -y \
  net-tools curl wget

# -----------------------------
# Quality of life
# -----------------------------
sudo apt install -y \
  terminator gnome-tweaks gparted \
  meld vlc fonts-firacode

echo "===== Done! All utilities installed. ====="
