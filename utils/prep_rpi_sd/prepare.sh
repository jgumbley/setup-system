#!/usr/bin/env bash
set -euo pipefail

device="$1"
image="$2"
key_dir="$3"
boot_partition="${device}1"
mount_dir="$(pwd)/.boot"

if [ ! -b "$device" ]; then
  echo "$device is not a block device" >&2
  exit 2
fi

if [ "$(lsblk -dnro TYPE "$device")" != disk ]; then
  echo "$device is not a whole disk" >&2
  exit 2
fi

if [ "$(lsblk -dnro RM "$device")" != 1 ]; then
  echo "$device is not marked removable" >&2
  exit 2
fi

if lsblk -nrpo MOUNTPOINTS "$device" | grep -q '[^[:space:]]'; then
  echo "$device or one of its partitions is mounted" >&2
  exit 2
fi

sudo xz --decompress --stdout "$image" | sudo dd of="$device" bs=16M conv=fsync status=progress
sudo partprobe "$device"
sudo udevadm settle

mkdir -p "$mount_dir"
cleanup() {
  if mountpoint -q "$mount_dir"; then
    sudo umount "$mount_dir"
  fi
  rmdir "$mount_dir"
}
trap cleanup EXIT
sudo mount "$boot_partition" "$mount_dir"

user_data="$(mktemp .user-data.XXXXXX)"
trap 'rm -f "$user_data"; cleanup' EXIT
{
  printf '%s\n' '#cloud-config'
  printf '%s\n' 'hostname: legobrick'
  printf '%s\n' 'fqdn: legobrick'
  printf '%s\n' 'manage_etc_hosts: true'
  printf '%s\n' 'ssh_pwauth: false'
  printf '%s\n' 'users:'
  printf '%s\n' '  - name: system'
  printf '%s\n' '    groups: [adm, audio, cdrom, dialout, sudo]'
  printf '%s\n' '    shell: /bin/bash'
  printf '%s\n' '    lock_passwd: true'
  printf '%s\n' '    sudo: ALL=(ALL) NOPASSWD:ALL'
  printf '%s\n' '    ssh_authorized_keys:'
  for key in "$key_dir"/*.pub; do
    printf '      - %s\n' "$(<"$key")"
  done
  printf '%s\n' 'package_update: true'
  printf '%s\n' 'packages: [git, make]'
  printf '%s\n' 'power_state:'
  printf '%s\n' '  mode: reboot'
} > "$user_data"

sudo install -m 0644 "$user_data" "$mount_dir/user-data"
sudo tee "$mount_dir/network-config" >/dev/null <<'EOF'
network:
  version: 2
  ethernets:
    ethernet:
      match:
        name: "e*"
      dhcp4: true
EOF
sudo tee "$mount_dir/meta-data" >/dev/null <<'EOF'
instance-id: legobrick
local-hostname: legobrick
EOF
sudo cmp "$user_data" "$mount_dir/user-data"
sudo grep -qx 'local-hostname: legobrick' "$mount_dir/meta-data"
sudo grep -qx '      dhcp4: true' "$mount_dir/network-config"
sync
sudo umount "$mount_dir"

sudo fsck.vfat -n "$boot_partition"
sudo udisksctl power-off --block-device "$device"
echo "legobrick SD card prepared and powered off"
