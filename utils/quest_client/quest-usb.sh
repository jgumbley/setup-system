#!/usr/bin/env bash
set -euo pipefail

rule_file="/etc/udev/rules.d/51-meta-quest.rules"
rule='SUBSYSTEM=="usb", ATTR{idVendor}=="2833", MODE="0660", GROUP="plugdev", TAG+="uaccess"'

require() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf 'missing required command: %s\n' "$1" >&2
    exit 127
  fi
}

require lsusb
require adb
require sudo
require udevadm
require grep

printf 'Checking for Meta Quest over USB...\n'
if ! quest_lines="$(lsusb | grep -E '2833:501[23].*Quest')"; then
  printf 'No Meta Quest USB device found. Plug in the headset and rerun this script.\n' >&2
  exit 1
fi
printf '%s\n' "$quest_lines"

devices="$(adb devices -l)"
if printf '%s\n' "$devices" | grep -Eq '^[[:alnum:]]+[[:space:]]+device([[:space:]]|$)'; then
  printf 'ADB already has an authorized Quest USB transport:\n'
  printf '%s\n' "$devices"
  exit 0
fi

printf 'Installing Meta Quest udev rule for plugdev access...\n'
printf '%s\n' "$rule" | sudo tee "$rule_file" >/dev/null
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=usb --attr-match=idVendor=2833

printf 'Restarting ADB and checking USB transport...\n'
adb kill-server
adb start-server
devices="$(adb devices -l)"
printf '%s\n' "$devices"

if printf '%s\n' "$devices" | grep -Eq '^[[:alnum:]]+[[:space:]]+device([[:space:]]|$)'; then
  exit 0
fi

if printf '%s\n' "$devices" | grep -q 'unauthorized'; then
  printf 'ADB sees the Quest, but the headset has not authorized this host. Accept the RSA prompt in-headset and rerun this script.\n' >&2
  exit 1
fi

if printf '%s\n' "$devices" | grep -q 'no permissions'; then
  printf 'ADB still lacks USB node permissions. Unplug/replug the Quest, then rerun this script.\n' >&2
  exit 1
fi

printf 'ADB did not list an authorized Quest device.\n' >&2
exit 1
