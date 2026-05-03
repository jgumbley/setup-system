#!/usr/bin/env bash
set -euo pipefail

echo "[1/3] Installing packages with pkg..."
pkg install -y git openssh

echo "[2/3] Generating SSH key..."
mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"
if [ -e "$HOME/.ssh/id_ed25519" ] || [ -e "$HOME/.ssh/id_ed25519.pub" ]; then
  echo "Existing SSH key found at ~/.ssh/id_ed25519. Remove or rename it, then rerun."
  exit 1
fi
ssh-keygen -t ed25519 -f "$HOME/.ssh/id_ed25519" -N "" -C "termux@$(hostname)"

echo "[3/3] Public key:"
cat "$HOME/.ssh/id_ed25519.pub"
