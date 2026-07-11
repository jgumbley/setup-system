#!/usr/bin/env bash
set -euo pipefail

device="$1"
image="$2"

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

sudo dd if="$image" of="$device" bs=16M conv=fsync status=progress
sudo cmp --bytes "$(stat -c %s "$image")" "$image" "$device"
sudo udisksctl power-off --block-device "$device"
echo "rocks Ubuntu installer USB prepared, verified, and powered off"
