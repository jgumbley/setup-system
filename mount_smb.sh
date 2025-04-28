#!/bin/bash

# Settings from NAS config
NAS_HOST="192.168.1.10"
NAS_SHARE="iceburg"
NAS_USER="admin"

# Prompt for password
read -s -p "Enter SMB password: " NAS_PASSWORD
echo

# Create mount point if it doesn't exist
MOUNT_POINT="$(pwd)/nas_mount"
mkdir -p "$MOUNT_POINT"

# Mount the SMB share
mount_smbfs "//$NAS_USER:$NAS_PASSWORD@$NAS_HOST/$NAS_SHARE" "$MOUNT_POINT"

if [ $? -eq 0 ]; then
  echo "Successfully mounted SMB share at $MOUNT_POINT"
else
  echo "Failed to mount SMB share"
  exit 1
fi
