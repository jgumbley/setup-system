SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

HOSTNAME := hal
LOCATIONS_FILE := /etc/setup-system/hal-locations.mk
PANE_SH := $(abspath $(CURDIR)/../../pane.sh)
USB_SCRIPT := $(CURDIR)/quest-usb.sh

-include $(LOCATIONS_FILE)

CLIENT_APK ?= $(HAL_OPENMW_ROOT)/apks/moonlight-v12.1-quest-v76-fix-nonroot.apk

.PHONY: help preflight adb-check apk-check usb-check check devices usb usb-pane install install-apply install-pane wireless-pair wireless-connect install-wireless mtp-enable

help:
	@echo "Targets:"
	@echo "  make check                         Validate HAL paths, ADB, APK, and USB helper"
	@echo "  make devices                       List connected ADB devices"
	@echo "  make usb-pane                      Prepare a USB-connected Quest in a pane"
	@echo "  make install-pane                  Install the Moonlight Quest APK over USB"
	@echo "  make wireless-pair IP_PORT=address:pair-port"
	@echo "  make wireless-connect IP_PORT=address:adb-port"
	@echo "  make install-wireless IP_PORT=address:adb-port"
	@echo "  make mtp-enable                    Switch the connected Quest to MTP"

preflight:
	@test "$$(hostname)" = "$(HOSTNAME)" || { echo "This utility only supports $(HOSTNAME)." >&2; exit 1; }
	@test -f "$(LOCATIONS_FILE)" || { echo "Missing Ansible-managed locations: $(LOCATIONS_FILE). Run make setup first." >&2; exit 2; }
	@test -n "$(HAL_OPENMW_ROOT)" || { echo "Missing HAL_OPENMW_ROOT in $(LOCATIONS_FILE)." >&2; exit 2; }

adb-check: preflight
	@command -v adb >/dev/null || { echo "adb is required; run make setup." >&2; exit 127; }

apk-check: adb-check
	@test -f "$(CLIENT_APK)" || { echo "Missing Quest client APK: $(CLIENT_APK)" >&2; exit 2; }

usb-check: adb-check
	@test -f "$(USB_SCRIPT)" || { echo "Missing Quest USB helper: $(USB_SCRIPT)" >&2; exit 2; }
	bash -n "$(USB_SCRIPT)"

check: usb-check apk-check
	@echo "Quest client utility verified."

devices: adb-check
	adb devices -l

usb: usb-check
	bash "$(USB_SCRIPT)"

usb-pane: usb-check
	bash "$(PANE_SH)" quest-usb $(MAKE) --no-print-directory usb

install: apk-check usb
	adb install -r "$(CLIENT_APK)"

install-apply: install
	@:

install-pane: usb-check apk-check
	bash "$(PANE_SH)" quest-client-install $(MAKE) --no-print-directory install-apply

wireless-pair: adb-check
	@test -n "$(IP_PORT)" || { echo "usage: make wireless-pair IP_PORT=address:pair-port" >&2; exit 2; }
	adb pair "$(IP_PORT)"

wireless-connect: adb-check
	@test -n "$(IP_PORT)" || { echo "usage: make wireless-connect IP_PORT=address:adb-port" >&2; exit 2; }
	adb connect "$(IP_PORT)"
	adb devices -l

install-wireless: apk-check wireless-connect
	adb install -r "$(CLIENT_APK)"

mtp-enable: adb-check
	adb shell svc usb setFunctions mtp
	adb shell settings put global adb_enabled 1
	adb devices -l
