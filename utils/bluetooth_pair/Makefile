SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

HOSTNAME := rocks
PYTHON := /usr/bin/python3
CONTROLLER := $(CURDIR)/xbox_controller.py
BLUEZ_INPUT_CONFIG := /etc/bluetooth/input.conf
UDEV_RULE := /etc/udev/rules.d/70-xbox-controller.rules

.PHONY: help preflight check pair_controller pair_controller-run pair_controller-pane

help:
	@echo "Targets:"
	@echo "  make check            Verify the Xbox controller utility"
	@echo "  make pair_controller  Pair, reconnect, and test the Xbox controller"
	@echo "  make pair_controller-pane  Run pair_controller in an agent pane"

preflight:
	@test "$$(hostname)" = "$(HOSTNAME)" || { echo "Xbox controller pairing is only supported on $(HOSTNAME)." >&2; exit 1; }
	@test -x "$(PYTHON)" || { echo "$(PYTHON) is unavailable; run make setup first." >&2; exit 127; }
	@systemctl is-active --quiet bluetooth.service || { echo "bluetooth.service is not active; run make setup first." >&2; exit 1; }
	@$(PYTHON) -c 'import dbus, evdev, gi' || { echo "Python Bluetooth/input dependencies are unavailable; run make setup first." >&2; exit 127; }
	@grep -Fxq 'ClassicBondedOnly=false' "$(BLUEZ_INPUT_CONFIG)" || { echo "BlueZ Xbox support is not configured; run make setup first." >&2; exit 1; }
	@test -f "$(UDEV_RULE)" || { echo "Xbox input permissions are not configured; run make setup first." >&2; exit 1; }
	@grep -Fq 'ENV{ID_INPUT_JOYSTICK}="1"' "$(UDEV_RULE)" || { echo "Xbox input is not classified as a joystick; run make setup first." >&2; exit 1; }

check: preflight
	@$(PYTHON) -c 'compile(open("$(CONTROLLER)", encoding="utf-8").read(), "$(CONTROLLER)", "exec")'
	@echo "Xbox controller utility verified."

pair_controller:
	@status=0; $(MAKE) --no-print-directory pair_controller-run || status=$$?; \
		if [ "$$status" -ne 0 ]; then \
			printf '\nThe Xbox controller utility failed. Press Enter to close.\n'; \
			read -r _; \
		fi; \
		exit "$$status"

pair_controller-run: preflight
	"$(PYTHON)" -B "$(CONTROLLER)"

pair_controller-pane: preflight
	bash ../../pane.sh pair-controller $(MAKE) --no-print-directory pair_controller-run
