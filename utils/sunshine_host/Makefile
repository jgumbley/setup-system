SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

HOSTNAME := hal
CONFIG_DIR := /etc/sunshine-host
STATE_DIR := /var/lib/sunshine-host
RUNTIME_DIR := /run/sunshine-host
COVERS_DIR := $(CURDIR)/covers
SUNSHINE_HOST ?= localhost
SUNSHINE_USERNAME ?= sunshine
SUNSHINE_PASSWORD ?= $(PASSWORD)
SUNSHINE_PIN_NAME ?= $(or $(NAME),moonlight)

.PHONY: help preflight covers check status verify pairings pin

help:
	@echo "Targets:"
	@echo "  make covers                  Regenerate the committed Moonlight cover art"
	@echo "  make check                   Check the utility source and cover inventory"
	@echo "  make status                  Show HAL's installed Sunshine host status"
	@echo "  make verify                  Verify the installed boot-time host"
	@echo "  make pairings                Summarize paired clients from live state"
	@echo "  make pin PIN=1234 PASSWORD=... [NAME=client]"

preflight:
	@test "$$(hostname)" = "$(HOSTNAME)" || { echo "This utility only supports $(HOSTNAME)." >&2; exit 1; }

covers: preflight
	python3 -B make_covers.py "$(COVERS_DIR)"

check: preflight
	bash -n wait-runtime-sockets.sh
	@python3 -B sunshine_pairings_status.py /does/not/exist >/dev/null
	@for name in eaadwig tmux morrowind quake3 rocknix; do \
		test -f "$(COVERS_DIR)/$$name.png" || { echo "Missing cover: $(COVERS_DIR)/$$name.png" >&2; exit 1; }; \
	done

status: preflight
	@printf 'Target:   '; systemctl is-enabled sunshine-host.target
	@printf 'Sway:     '; systemctl is-active sunshine-host-sway.service
	@printf 'Sunshine: '; systemctl is-active sunshine-host-sunshine.service
	@printf 'Wayland:  '; test -S "$(RUNTIME_DIR)/wayland-1" && echo ready || echo missing
	@printf 'D-Bus:    '; test -S "$(RUNTIME_DIR)/bus" && echo ready || echo missing
	@systemctl --no-pager --full status sunshine-host.target sunshine-host-sway.service sunshine-host-sunshine.service

verify: preflight
	@test "$$(systemctl is-enabled sunshine-host.target)" = enabled
	@test "$$(systemctl is-active sunshine-host-sway.service)" = active
	@test "$$(systemctl is-active sunshine-host-sunshine.service)" = active
	@test -S "$(RUNTIME_DIR)/wayland-1"
	@test -S "$(RUNTIME_DIR)/bus"
	@test -f "$(CONFIG_DIR)/apps.json"
	@test -f "$(STATE_DIR)/sunshine_state.json"
	@python3 -c 'import json; data = json.load(open("$(CONFIG_DIR)/apps.json", encoding="utf-8")); assert [app["name"] for app in data["apps"]] == ["eaadwig", "tmux", "morrowind", "quake3", "rocknix"]'
	@for launcher in /usr/lib/sunshine-host/bin/*.sh; do bash -n "$$launcher"; done
	@ss -ltn | awk '$$4 ~ /:47990$$/ { found = 1 } END { exit !found }'
	@! grep -R -F '/home/system/wip/platform/sunshine-host' "$(CONFIG_DIR)" /usr/lib/sunshine-host
	@echo "Sunshine host verified."

pairings: preflight
	@test -f "$(STATE_DIR)/sunshine_state.json" || { echo "Missing Sunshine state: $(STATE_DIR)/sunshine_state.json" >&2; exit 1; }
	@python3 -B sunshine_pairings_status.py "$(STATE_DIR)"

pin: preflight
	@test -n "$(PIN)" || { echo "usage: make pin PIN=1234 PASSWORD=... [NAME=client]" >&2; exit 2; }
	@test -n "$(SUNSHINE_PASSWORD)" || { echo "PASSWORD is required." >&2; exit 2; }
	@command -v curl >/dev/null
	@host="$(SUNSHINE_HOST)"; user="$(SUNSHINE_USERNAME)"; pass="$(SUNSHINE_PASSWORD)"; \
		pin="$(PIN)"; name="$(SUNSHINE_PIN_NAME)"; url="https://$$host:47990"; \
		jar="$$(mktemp)"; trap 'rm -f "$$jar"' EXIT; \
		response="$$(curl -sk -c "$$jar" -u "$$user:$$pass" "$$url/api/csrf-token")"; \
		token="$$(printf '%s' "$$response" | sed -n 's/.*"csrf_token"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p; s/.*"token"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)"; \
		test -n "$$token" || { echo "Failed to obtain a Sunshine CSRF token." >&2; exit 1; }; \
		body="$$(printf '{"pin":"%s","name":"%s"}' "$$pin" "$$name")"; \
		output="$$(curl -sk -b "$$jar" -u "$$user:$$pass" -H 'Content-Type: application/json' -H "X-CSRF-Token: $$token" -X POST --data "$$body" "$$url/api/pin")"; \
		printf '%s\n' "$$output"; \
		case "$$output" in *'"status":true'*|*'"status": true'*|*'"status_code":200'*) exit 0 ;; esac; \
		echo "Pairing did not report success." >&2; exit 1
