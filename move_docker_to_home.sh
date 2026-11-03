#!/usr/bin/env bash
# Move Docker and containerd storage off the 25 GB root volume onto /home (68 GB) on a
# VCM Ubuntu 24 VM. XFS cannot shrink, so /home's space cannot be given to root; instead
# /var/lib/docker and /var/lib/containerd become bind mounts of directories on /home.
#
# Usage: ./move_docker_to_home.sh          keep existing images (copies them to /home)
#        ./move_docker_to_home.sh --reset  discard all images and containers instead
set -euo pipefail

dest=/home/docker-storage
reset=false
[[ "${1:-}" == "--reset" ]] && reset=true

sudo systemctl stop docker.socket docker containerd

for d in docker containerd; do
  src=/var/lib/$d
  if mountpoint -q "$src"; then
    echo "$src is already a mount; skipping"
    continue
  fi
  sudo mkdir -p "$dest/$d"
  if $reset; then
    sudo rm -rf "$src"
  elif [[ -d "$src" ]]; then
    sudo rsync -aHAX "$src/" "$dest/$d/"
    sudo rm -rf "$src"
  fi
  sudo mkdir -p "$src"
  grep -q "^$dest/$d " /etc/fstab ||
    echo "$dest/$d $src none bind,x-systemd.requires-mounts-for=/home 0 0" | sudo tee -a /etc/fstab
done

sudo systemctl daemon-reload
mountpoint -q /var/lib/containerd || sudo mount /var/lib/containerd
mountpoint -q /var/lib/docker || sudo mount /var/lib/docker
sudo systemctl start containerd docker

sudo docker info --format 'Docker root: {{.DockerRootDir}}'  # sudo: docker group membership added by vm_setup.sh does not apply to the current session
findmnt --target /var/lib/docker
findmnt --target /var/lib/containerd
df -h / /home
