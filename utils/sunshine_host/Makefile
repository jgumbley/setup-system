SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

HOSTNAME := holly
CONFIG_DIR := /etc/sunshine-host
STATE_DIR := /var/lib/sunshine-host
CREDENTIALS_FILE := $(STATE_DIR)/web-manager-password
RUNTIME_DIR := /run/sunshine-host
COVERS_DIR := $(CURDIR)/covers
SUNSHINE_HOST ?= localhost
SUNSHINE_USERNAME ?= sunshine
SUNSHINE_PIN_NAME ?= $(or $(NAME),moonlight)
SWAY_SOCKET := $(firstword $(wildcard $(RUNTIME_DIR)/sway-ipc.*.sock))

.PHONY: help preflight sway-preflight covers check status session-layout steam-game-fullscreen verify pairings api-check pin

help:
	@echo "Targets:"
	@echo "  make covers                  Regenerate the committed Moonlight cover art"
	@echo "  make check                   Check the utility source and cover inventory"
	@echo "  make status                  Show Holly's installed Sunshine host status"
	@echo "  make session-layout          Show live Steam and Steam-game Sway windows"
	@echo "  make steam-game-fullscreen   Register the rule and fullscreen the live Steam game"
	@echo "  make verify                  Verify the installed boot-time host"
	@echo "  make pairings                Summarize paired clients from live state"
	@echo "  make api-check               Verify managed Sunshine API authentication"
	@echo "  make pin PIN=1234 [NAME=client]"

preflight:
	@test "$$(hostname)" = "$(HOSTNAME)" || { echo "This utility only supports $(HOSTNAME)." >&2; exit 1; }

sway-preflight: preflight
	@test -S "$(SWAY_SOCKET)" || { echo "Expected exactly one live Sway IPC socket under $(RUNTIME_DIR)." >&2; exit 1; }
	@test "$$(find "$(RUNTIME_DIR)" -maxdepth 1 -type s -name 'sway-ipc.*.sock' | wc -l)" -eq 1 || { echo "Expected exactly one live Sway IPC socket under $(RUNTIME_DIR)." >&2; exit 1; }
	@command -v swaymsg >/dev/null
	@command -v jq >/dev/null

covers: preflight
	python3 -B make_covers.py "$(COVERS_DIR)"

check: preflight
	bash -n wait-runtime-sockets.sh
	bash -n ../../roles/sunshine-host/templates/run-rocknix.sh.j2
	@python3 -B sunshine_pairings_status.py /does/not/exist >/dev/null
	@grep -Fxq 'controller = enabled' ../../roles/sunshine-host/templates/sunshine.conf.j2
	@grep -Fxq 'gamepad = xone' ../../roles/sunshine-host/templates/sunshine.conf.j2
	@grep -Fq 'Sunshine\ X-Box\ One\ \(virtual\)\ pad' ../../roles/sunshine-host/templates/run-rocknix.sh.j2
	@grep -Fq '[[ -r "/dev/input/$$event_name" ]]' ../../roles/sunshine-host/templates/run-rocknix.sh.j2
	@grep -Fq 'for_window [class="^steam_app_[0-9]+$$"] fullscreen enable' ../../roles/sunshine-host/templates/sway.conf.j2
	@for name in eaadwig philby camera morrowind quake3 rocknix steam; do \
		test -f "$(COVERS_DIR)/$$name.png" || { echo "Missing cover: $(COVERS_DIR)/$$name.png" >&2; exit 1; }; \
	done

status: preflight
	@printf 'Target:   '; systemctl is-enabled sunshine-host.target
	@printf 'Sway:     '; systemctl is-active sunshine-host-sway.service
	@printf 'Sunshine: '; systemctl is-active sunshine-host-sunshine.service
	@printf 'Wayland:  '; test -S "$(RUNTIME_DIR)/wayland-1" && echo ready || echo missing
	@printf 'D-Bus:    '; test -S "$(RUNTIME_DIR)/bus" && echo ready || echo missing
	@systemctl --no-pager --full status sunshine-host.target sunshine-host-sway.service sunshine-host-sunshine.service

session-layout: sway-preflight
	@swaymsg -s "$(SWAY_SOCKET)" -t get_tree -r | jq '[.. | objects | select(.type == "con" and ((.window_properties.class? // "") | test("^(steam|steam_app_[0-9]+)$$"))) | {id, name, class: .window_properties.class, focused, fullscreen_mode, visible, rect}]'

steam-game-fullscreen: sway-preflight
	@swaymsg -s "$(SWAY_SOCKET)" -t get_tree -r | jq -e '[.. | objects | select(.type == "con" and ((.window_properties.class? // "") | test("^steam_app_[0-9]+$$")))] | length > 0' >/dev/null || { echo "No live Steam game window was found; nothing changed." >&2; exit 1; }
	@swaymsg -s "$(SWAY_SOCKET)" 'for_window [class="^steam_app_[0-9]+$$"] fullscreen enable'
	@swaymsg -s "$(SWAY_SOCKET)" '[class="^steam_app_[0-9]+$$"] fullscreen enable'
	@swaymsg -s "$(SWAY_SOCKET)" -t get_tree -r | jq -e '[.. | objects | select(.type == "con" and ((.window_properties.class? // "") | test("^steam_app_[0-9]+$$")))] | (length > 0) and all(.[]; .fullscreen_mode == 1)' >/dev/null
	@$(MAKE) --no-print-directory session-layout

verify: preflight
	@test "$$(systemctl is-enabled sunshine-host.target)" = enabled
	@test "$$(systemctl is-active sunshine-host-sway.service)" = active
	@test "$$(systemctl is-active sunshine-host-sunshine.service)" = active
	@test -S "$(RUNTIME_DIR)/wayland-1"
	@test -S "$(RUNTIME_DIR)/bus"
	@test -f "$(CONFIG_DIR)/apps.json"
	@test -f "$(STATE_DIR)/sunshine_state.json"
	@test "$$(stat -c '%U:%G:%a' "$(STATE_DIR)/sunshine_state.json")" = system:system:600
	@test -s "$(CREDENTIALS_FILE)"
	@test "$$(stat -c '%U:%G:%a' "$(CREDENTIALS_FILE)")" = system:system:600
	@test -c /dev/uinput -a -r /dev/uinput -a -w /dev/uinput
	@test -c /dev/uhid -a -r /dev/uhid -a -w /dev/uhid
	@grep -Fxq 'controller = enabled' "$(CONFIG_DIR)/sunshine.conf"
	@grep -Fxq 'gamepad = xone' "$(CONFIG_DIR)/sunshine.conf"
	@grep -Fq 'Sunshine\ X-Box\ One\ \(virtual\)\ pad' /usr/lib/sunshine-host/bin/run-rocknix.sh
	@command -v steam >/dev/null
	@command -v firefox >/dev/null
	@python3 -c 'import json; data = json.load(open("$(CONFIG_DIR)/apps.json", encoding="utf-8")); assert [app["name"] for app in data["apps"]] == ["eaadwig", "philby", "camera", "morrowind", "quake3", "rocknix", "steam"]'
	@for launcher in /usr/lib/sunshine-host/bin/*.sh; do bash -n "$$launcher"; done
	@ss -ltn | awk '$$4 ~ /:47990$$/ { found = 1 } END { exit !found }'
	@! grep -R -F '/home/system/wip/platform/sunshine-host' "$(CONFIG_DIR)" /usr/lib/sunshine-host
	@echo "Sunshine host verified."

pairings: preflight
	@test -f "$(STATE_DIR)/sunshine_state.json" || { echo "Missing Sunshine state: $(STATE_DIR)/sunshine_state.json" >&2; exit 1; }
	@python3 -B sunshine_pairings_status.py "$(STATE_DIR)"

api-check: preflight
	@test -s "$(CREDENTIALS_FILE)" || { echo "Missing managed Sunshine credential; run make setup first." >&2; exit 2; }
	@command -v curl >/dev/null
	@host="$(SUNSHINE_HOST)"; user="$(SUNSHINE_USERNAME)"; pass="$$(cat "$(CREDENTIALS_FILE)")"; url="https://$$host:47990"; \
		auth_file="$$(mktemp)"; trap 'rm -f "$$auth_file"' EXIT; \
		printf 'user = "%s:%s"\n' "$$user" "$$pass" > "$$auth_file"; \
		status="$$(curl -sk --config "$$auth_file" -o /dev/null -w '%{http_code}' -H "Origin: $$url" -H "Referer: $$url/" "$$url/api/config")"; \
		test "$$status" = 200 || { echo "Sunshine API authentication returned HTTP $$status; run make setup first." >&2; exit 1; }; \
		echo "Sunshine API authentication verified."

pin: preflight
	@test -n "$(PIN)" || { echo "usage: make pin PIN=1234 [NAME=client]" >&2; exit 2; }
	@test "$$(printf '%s' "$(PIN)" | wc -c)" -eq 4 || { echo "PIN must contain exactly four digits." >&2; exit 2; }
	@printf '%s' "$(PIN)" | grep -Eq '^[0-9]{4}$$' || { echo "PIN must contain exactly four digits." >&2; exit 2; }
	@$(MAKE) --no-print-directory api-check
	@command -v curl >/dev/null
	@host="$(SUNSHINE_HOST)"; user="$(SUNSHINE_USERNAME)"; pass="$$(cat "$(CREDENTIALS_FILE)")"; \
		pin="$(PIN)"; name="$(SUNSHINE_PIN_NAME)"; url="https://$$host:47990"; \
		auth_file="$$(mktemp)"; response_file="$$(mktemp)"; trap 'rm -f "$$auth_file" "$$response_file"' EXIT; \
		printf 'user = "%s:%s"\n' "$$user" "$$pass" > "$$auth_file"; \
		body="$$(python3 -c 'import json, sys; print(json.dumps({"pin": sys.argv[1], "name": sys.argv[2]}))' "$$pin" "$$name")"; \
		status="$$(curl -sk --config "$$auth_file" -o "$$response_file" -w '%{http_code}' -H "Origin: $$url" -H "Referer: $$url/pin" -H 'Content-Type: application/json' -X POST --data "$$body" "$$url/api/pin")"; \
		output="$$(cat "$$response_file")"; \
		printf '%s\n' "$$output"; \
		test "$$status" = 200 || { echo "Sunshine PIN API returned HTTP $$status; run make setup and retry with a fresh PIN." >&2; exit 1; }; \
		case "$$output" in *'"status":true'*|*'"status": true'*|*'"status_code":200'*) exit 0 ;; esac; \
		echo "Sunshine rejected the PIN; generate a fresh PIN and retry." >&2; exit 1
