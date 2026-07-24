SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

HOSTNAME := rocks
PAIR_SCRIPT := $(CURDIR)/pair.sh
XBOX_PRO_CONTROLLER_NAME := Xbox Elite Wireless Controller

.PHONY: help preflight check pair pair-apply pair-xbox-pro-controller

help:
	@echo "Targets:"
	@echo "  make check                     Verify Bluetooth pairing prerequisites"
	@echo "  make pair DEVICE_NAME='name'   Pair one discoverable Bluetooth device"
	@echo "  make pair-xbox-pro-controller  Pair an Xbox Elite wireless controller"

preflight:
	@test "$$(hostname)" = "$(HOSTNAME)" || { echo "Bluetooth pairing is only supported on $(HOSTNAME)." >&2; exit 1; }
	@command -v bluetoothctl >/dev/null || { echo "bluetoothctl is unavailable; run make setup first." >&2; exit 127; }
	@systemctl is-active --quiet bluetooth.service || { echo "bluetooth.service is not active; run make setup first." >&2; exit 1; }
	@bluetoothctl show >/dev/null || { echo "No Bluetooth controller is available." >&2; exit 1; }

check: preflight
	bash -n "$(PAIR_SCRIPT)"
	@echo "Bluetooth pairing utility verified."

pair:
	@test -n "$(DEVICE_NAME)" || { echo "usage: make pair DEVICE_NAME='advertised device name'" >&2; exit 2; }
	bash ../../pane.sh bluetooth-pair $(MAKE) --no-print-directory pair-apply DEVICE_NAME="$(DEVICE_NAME)"

pair-apply: preflight
	bash "$(PAIR_SCRIPT)" "$(DEVICE_NAME)"

pair-xbox-pro-controller:
	$(MAKE) --no-print-directory pair DEVICE_NAME="$(XBOX_PRO_CONTROLLER_NAME)"
