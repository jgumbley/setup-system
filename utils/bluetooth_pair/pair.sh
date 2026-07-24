#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ] || [ -z "$1" ]; then
  echo "usage: pair.sh <advertised-device-name>" >&2
  exit 2
fi

device_name="$1"

echo "Put ${device_name} into Bluetooth pairing mode."
echo "Scanning for 20 seconds..."
bluetoothctl power on
bluetoothctl --timeout 20 scan on

mapfile -t addresses < <(
  while read -r kind address name; do
    if [ "$kind" = "Device" ] && [ "$name" = "$device_name" ]; then
      printf '%s\n' "$address"
    fi
  done < <(bluetoothctl devices)
)

if [ "${#addresses[@]}" -eq 0 ]; then
  echo "No Bluetooth device named '${device_name}' was discovered." >&2
  exit 1
fi

if [ "${#addresses[@]}" -ne 1 ]; then
  echo "Expected one Bluetooth device named '${device_name}', found ${#addresses[@]}: ${addresses[*]}" >&2
  exit 1
fi

address="${addresses[0]}"

bluetoothctl --agent NoInputNoOutput --timeout 30 pair "$address"
bluetoothctl trust "$address"
bluetoothctl connect "$address"

device_info="$(bluetoothctl info "$address")"
printf '%s\n' "$device_info"
grep -Eq '^[[:space:]]*Paired: yes$' <<<"$device_info"
grep -Eq '^[[:space:]]*Trusted: yes$' <<<"$device_info"
grep -Eq '^[[:space:]]*Connected: yes$' <<<"$device_info"

echo "Paired, trusted, and connected ${device_name} (${address})."
