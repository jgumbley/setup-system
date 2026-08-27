SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

HOSTNAME := holly
CONFIG_DIR := /etc/sunshine-host
STATE_DIR := /var/lib/sunshine-host
CREDENTIALS_FILE := $(STATE_DIR)/web-manager-password
RUNTIME_DIR := /run/sunshine-host
COVERS_DIR := $(CURDIR)/covers
QUAKE3_AUTOEXEC_SOURCE := ../game_runtimes/autoexec.cfg
QUAKE3_AUTOEXEC_INSTALLED := $(STATE_DIR)/games/quake3/home/baseq3/autoexec.cfg
QUAKE3_SESSION_LOG := /var/cache/sunshine-host/games/quake3/session.log
ROCKNIX_SESSION_LOG := /var/cache/sunshine-host/games/rocknix/session.log
SUNSHINE_HOST ?= localhost
SUNSHINE_USERNAME ?= sunshine
SUNSHINE_PIN_NAME ?= $(or $(NAME),moonlight)
SWAY_SOCKET := $(firstword $(wildcard $(RUNTIME_DIR)/sway-ipc.*.sock))

.PHONY: help preflight sway-preflight covers check status quake3-log rocknix-log session-layout steam-game-fullscreen verify pairings api-check pin reboot reboot-apply

help:
	@echo "Targets:"
	@echo "  make covers                  Regenerate the committed Moonlight cover art"
	@echo "  make check                   Check the utility source and cover inventory"
	@echo "  make status                  Show Holly's installed Sunshine host status"
	@echo "  make quake3-log              Show the current Quake III Moonlight session log"
	@echo "  make rocknix-log             Show the current ROCKNIX Moonlight session log"
	@echo "  make session-layout          Show live application windows in the Sunshine Sway session"
	@echo "  make steam-game-fullscreen   Register the rule and fullscreen the live Steam game"
	@echo "  make verify                  Verify the installed boot-time host"
	@echo "  make pairings                Summarize paired clients from live state"
	@echo "  make api-check               Verify managed Sunshine API authentication"
	@echo "  make pin PIN=1234 [NAME=client]"
	@echo "  make reboot                  Reboot Holly after a kernel configuration change"

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
	bash -n ../../roles/sunshine-host/templates/game-session.sh.j2
	bash -n ../../roles/sunshine-host/templates/run-morrowind-openmw.sh.j2
	bash -n ../../roles/sunshine-host/templates/run-quake3.sh.j2
	bash -n ../../roles/sunshine-host/templates/run-rocknix.sh.j2
	@python3 -B sunshine_pairings_status.py /does/not/exist >/dev/null
	@grep -Fxq 'controller = enabled' ../../roles/sunshine-host/templates/sunshine.conf.j2
	@grep -Fxq 'gamepad = xone' ../../roles/sunshine-host/templates/sunshine.conf.j2
	@grep -Fq 'Sunshine*\(virtual\)*pad*' ../../roles/sunshine-host/templates/game-session.sh.j2
	@grep -Fq '/sys/class/input/input*/name' ../../roles/sunshine-host/templates/game-session.sh.j2
	@grep -Fq 'event_device="/dev/input/$${event_link##*/}"' ../../roles/sunshine-host/templates/game-session.sh.j2
	@! grep -Eq 'game_session_start_controller_monitor|game_session_controller_monitors|controller-wait\.|/usr/bin/evtest|/usr/bin/stdbuf|/usr/bin/grep -m1' ../../roles/sunshine-host/templates/game-session.sh.j2
	@grep -Fq 'exec 9>&-' ../../roles/sunshine-host/templates/game-session.sh.j2
	@grep -Fq '/usr/bin/setsid' ../../roles/sunshine-host/templates/game-session.sh.j2
	@grep -Fq '/usr/bin/flock -n 9' ../../roles/sunshine-host/templates/game-session.sh.j2
	@grep -Fq 'game_session_acquire "QUAKE III ARENA"' ../../roles/sunshine-host/templates/run-quake3.sh.j2
	@grep -Fq 'game_session_require_runtime_contract' ../../roles/sunshine-host/templates/run-quake3.sh.j2
	@grep -Fq '8cd90faf798d94618c871bfb2049d70d4315ad30' ../../roles/sunshine-host/templates/run-quake3.sh.j2
	@grep -Fq 'wait "$${quake3_pid}"' ../../roles/sunshine-host/templates/run-quake3.sh.j2
	@grep -Fq 'QUAKE III ARENA: SESSION FAILED' ../../roles/sunshine-host/templates/run-quake3.sh.j2
	@! grep -Fq 'game_session_wait_for_controller "QUAKE III ARENA"' ../../roles/sunshine-host/templates/run-quake3.sh.j2
	@grep -Fq 'game_session_begin "ROCKNIX" "{{ sunshine_host_controller_preflight_enabled | bool | lower }}"' ../../roles/sunshine-host/templates/run-rocknix.sh.j2
	@grep -Fq 'game_session_begin "MORROWIND" "{{ sunshine_host_controller_preflight_enabled | bool | lower }}"' ../../roles/sunshine-host/templates/run-morrowind-openmw.sh.j2
	@grep -Fq 'game_session_require_readable_dir "{{ sunshine_host_roms_dir }}" "ROCKNIX"' ../../roles/sunshine-host/templates/run-rocknix.sh.j2
	@grep -Fq '25398f713308c384528ac44fcb7a1a876fae90ea' ../../roles/sunshine-host/templates/run-rocknix.sh.j2
	@grep -Fq '1f080a6cf2425cd055a7d7de5c6de06394427298e79a3ab875469c9b7971d6ca' ../../roles/sunshine-host/templates/run-rocknix.sh.j2
	@grep -Fq '{{ sunshine_host_roms_dir }}:/storage/roms:rw' ../../roles/sunshine-host/templates/run-rocknix.sh.j2
	@grep -Fq '{{ sunshine_host_rocknix_state_dir }}/saves:/storage/roms/saves' ../../roles/sunshine-host/templates/run-rocknix.sh.j2
	@grep -Fq '{{ sunshine_host_rocknix_state_dir }}/states:/storage/roms/savestates' ../../roles/sunshine-host/templates/run-rocknix.sh.j2
	@grep -Fq '{{ sunshine_host_rocknix_state_dir }}/screenshots:/storage/roms/screenshots' ../../roles/sunshine-host/templates/run-rocknix.sh.j2
	@grep -Fq '{{ sunshine_host_rocknix_dir }}/rootfs/usr/lib/libretro:/tmp/cores:ro' ../../roles/sunshine-host/templates/run-rocknix.sh.j2
	@grep -Fq '{{ sunshine_host_rocknix_state_dir }}/joypads:/tmp/joypads:ro' ../../roles/sunshine-host/templates/run-rocknix.sh.j2
	@grep -Fq '/usr/bin/cp -R "{{ sunshine_host_rocknix_dir }}/rootfs/usr/config/."' ../../roles/sunshine-host/templates/run-rocknix.sh.j2
	@grep -Fq -- '--cap-drop ALL' ../../roles/sunshine-host/templates/run-rocknix.sh.j2
	@grep -Fq -- '--security-opt no-new-privileges' ../../roles/sunshine-host/templates/run-rocknix.sh.j2
	@grep -Fq -- '--no-splash' ../../roles/sunshine-host/templates/run-rocknix.sh.j2
	@! grep -Fq -- '--privileged' ../../roles/sunshine-host/templates/run-rocknix.sh.j2
	@! grep -Eq 'openmw-portmaster|Morrowind\.sh|sunshine_host_rocknix_morrowind' ../../roles/sunshine-host/templates/run-rocknix.sh.j2
	@grep -Fq -- '--app-id=game-session-controller-required' ../../roles/sunshine-host/templates/game-session.sh.j2
	@grep -Fq 'This launch attempt will close after 30 seconds.' ../../roles/sunshine-host/templates/game-session.sh.j2
	@grep -Fq -- '--app-id=game-session-error' ../../roles/sunshine-host/templates/game-session.sh.j2
	@grep -Fq 'NO CONTROLLER DETECTED' ../../roles/sunshine-host/templates/game-session.sh.j2
	@grep -Fq 'exec /usr/bin/sleep 10' ../../roles/sunshine-host/templates/game-session.sh.j2
	@grep -Fq 'for_window [app_id="^game-session-controller-required$$"] fullscreen enable' ../../roles/sunshine-host/templates/sway.conf.j2
	@grep -Fq 'for_window [app_id="^game-session-error$$"] fullscreen enable' ../../roles/sunshine-host/templates/sway.conf.j2
	@grep -Fq 'setup-system/rocknix:20260718' ../../roles/sunshine-host/defaults/main.yml
	@grep -Fq 'sunshine_host_roms_dir: /mnt/iceburg/roms' ../../roles/sunshine-host/defaults/main.yml
	@grep -Fxq 'sunshine_host_controller_preflight_enabled: false' ../../roles/sunshine-host/defaults/main.yml
	@grep -Fq -- '- docker.io' ../../roles/sunshine-host/tasks/main.yml
	@! grep -Fq -- '- evtest' ../../roles/sunshine-host/tasks/main.yml
	@grep -Fq 'groups: input,render,video,audio,docker' ../../roles/sunshine-host/tasks/main.yml
	@grep -Fq 'sunshine-retroarch.cfg' ../../roles/sunshine-host/tasks/main.yml
	@grep -Fq 'input_device = "Sunshine X-Box One (virtual) pad"' ../../roles/sunshine-host/tasks/main.yml
	@grep -Fq '/openmw/current' ../../roles/sunshine-host/defaults/main.yml
	@for package in build-essential libasound2-dev libcurl4-openssl-dev libsdl2-dev libxrandr-dev libxxf86dga-dev libxxf86vm-dev mesa-common-dev patch pkg-config; do \
		grep -Fq -- "- $$package" ../../roles/sunshine-host/tasks/main.yml || { echo "Missing Quake3e build package contract: $$package" >&2; exit 1; }; \
	done
	@test -f "$(QUAKE3_AUTOEXEC_SOURCE)"
	@grep -Fq 'sunshine_host_game_runtimes_utility_dir: "{{ playbook_dir }}/utils/game_runtimes"' ../../roles/sunshine-host/defaults/main.yml
	@grep -Fq 'src: "{{ sunshine_host_game_runtimes_utility_dir }}/autoexec.cfg"' ../../roles/sunshine-host/tasks/main.yml
	@grep -Fq 'dest: "{{ sunshine_host_quake3_home_dir }}/{{ sunshine_host_quake3_basegame }}/autoexec.cfg"' ../../roles/sunshine-host/tasks/main.yml
	@! grep -Fq 'eaadwig' ../../roles/sunshine-host/templates/apps.json.j2
	@test ! -e ../../roles/sunshine-host/templates/run-eaadwig-openmw.sh.j2
	@grep -Fq 'for_window [class="^steam_app_[0-9]+$$"] fullscreen enable' ../../roles/sunshine-host/templates/sway.conf.j2
	@grep -Fq 'GRUB_CMDLINE_LINUX_DEFAULT="quiet amdgpu.runpm=0"' ../../roles/sunshine-host/tasks/main.yml
	@grep -Fq 'ansible.builtin.command: plymouth --ping' ../../roles/sunshine-host/tasks/main.yml
	@grep -Fq 'sunshine_host_plymouth_ping.rc == 0' ../../roles/sunshine-host/tasks/main.yml
	@grep -Fq 'ansible.builtin.command: plymouth quit' ../../roles/sunshine-host/tasks/main.yml
	@! grep -Fq 'GRUB_CMDLINE_LINUX_DEFAULT' ../../roles/hal_hardware/tasks/main.yml
	@for name in philby camera morrowind quake3 rocknix steam; do \
		test -f "$(COVERS_DIR)/$$name.png" || { echo "Missing cover: $(COVERS_DIR)/$$name.png" >&2; exit 1; }; \
	done
	@git diff --check -- ../../roles/sunshine-host/defaults/main.yml ../../roles/sunshine-host/tasks/main.yml Makefile

status: preflight
	@printf 'Target:   '; systemctl is-enabled sunshine-host.target
	@printf 'Sway:     '; systemctl is-active sunshine-host-sway.service
	@printf 'Sunshine: '; systemctl is-active sunshine-host-sunshine.service
	@printf 'Wayland:  '; test -S "$(RUNTIME_DIR)/wayland-1" && echo ready || echo missing
	@printf 'D-Bus:    '; test -S "$(RUNTIME_DIR)/bus" && echo ready || echo missing
	@systemctl --no-pager --full status sunshine-host.target sunshine-host-sway.service sunshine-host-sunshine.service

quake3-log: preflight
	@test -f "$(QUAKE3_SESSION_LOG)" || { echo "No Quake III Moonlight session log exists yet." >&2; exit 1; }
	@tail -n 240 "$(QUAKE3_SESSION_LOG)"

rocknix-log: preflight
	@test -f "$(ROCKNIX_SESSION_LOG)" || { echo "No ROCKNIX Moonlight session log exists yet." >&2; exit 1; }
	@tail -n 240 "$(ROCKNIX_SESSION_LOG)"

session-layout: sway-preflight
	@swaymsg -s "$(SWAY_SOCKET)" -t get_tree -r | jq '[.. | objects | select(.type == "con" and (((.app_id? // "") != "") or ((.window_properties.class? // "") != ""))) | {id, name, app_id, class: .window_properties.class, focused, fullscreen_mode, visible, rect}]'

steam-game-fullscreen: sway-preflight
	@swaymsg -s "$(SWAY_SOCKET)" -t get_tree -r | jq -e '[.. | objects | select(.type == "con" and ((.window_properties.class? // "") | test("^steam_app_[0-9]+$$")))] | length > 0' >/dev/null || { echo "No live Steam game window was found; nothing changed." >&2; exit 1; }
	@swaymsg -s "$(SWAY_SOCKET)" 'for_window [class="^steam_app_[0-9]+$$"] fullscreen enable'
	@swaymsg -s "$(SWAY_SOCKET)" '[class="^steam_app_[0-9]+$$"] fullscreen enable'
	@swaymsg -s "$(SWAY_SOCKET)" -t get_tree -r | jq -e '[.. | objects | select(.type == "con" and ((.window_properties.class? // "") | test("^steam_app_[0-9]+$$")))] | (length > 0) and all(.[]; .fullscreen_mode == 1)' >/dev/null
	@$(MAKE) --no-print-directory session-layout

verify: preflight
	@test "$$(systemctl is-enabled sunshine-host.target)" = enabled
	@test "$$(systemctl is-active sunshine-host.target)" = active
	@test "$$(systemctl is-active sunshine-host-sway.service)" = active
	@test "$$(systemctl is-active sunshine-host-sunshine.service)" = active
	@! grep -qw splash /proc/cmdline
	@test -S "$(RUNTIME_DIR)/wayland-1"
	@test -S "$(RUNTIME_DIR)/bus"
	@test -f "$(CONFIG_DIR)/apps.json"
	@test -f "$(STATE_DIR)/sunshine_state.json"
	@test "$$(stat -c '%U:%G:%a' "$(STATE_DIR)/sunshine_state.json")" = system:system:600
	@test -s "$(CREDENTIALS_FILE)"
	@test "$$(stat -c '%U:%G:%a' "$(CREDENTIALS_FILE)")" = system:system:600
	@test -c /dev/uinput -a -r /dev/uinput -a -w /dev/uinput
	@test -c /dev/uhid -a -r /dev/uhid -a -w /dev/uhid
	@grep -qw 'amdgpu.runpm=0' /proc/cmdline || { echo "Holly has not booted with amdgpu.runpm=0; reboot after make setup." >&2; exit 1; }
	@test -c /dev/dri/renderD128 -a -r /dev/dri/renderD128 -a -w /dev/dri/renderD128
	@runtime_status="$$(cat /sys/class/drm/renderD128/device/power/runtime_status)"; \
		test "$$runtime_status" != error || { echo "Holly's AMD render node is wedged; reboot before using Sunshine." >&2; exit 1; }
	@grep -Fxq 'controller = enabled' "$(CONFIG_DIR)/sunshine.conf"
	@grep -Fxq 'gamepad = xone' "$(CONFIG_DIR)/sunshine.conf"
	@grep -Fq 'Sunshine*\(virtual\)*pad*' /usr/lib/sunshine-host/bin/game-session.sh
	@grep -Fq '/sys/class/input/input*/name' /usr/lib/sunshine-host/bin/game-session.sh
	@grep -Fq 'event_device="/dev/input/$${event_link##*/}"' /usr/lib/sunshine-host/bin/game-session.sh
	@! grep -Eq 'game_session_start_controller_monitor|game_session_controller_monitors|controller-wait\.|/usr/bin/evtest|/usr/bin/stdbuf|/usr/bin/grep -m1' /usr/lib/sunshine-host/bin/game-session.sh
	@grep -Fq '/usr/bin/flock -n 9' /usr/lib/sunshine-host/bin/game-session.sh
	@! grep -Fq 'game_session_wait_for_controller "QUAKE III ARENA"' /usr/lib/sunshine-host/bin/run-quake3.sh
	@grep -Fq 'game_session_begin "ROCKNIX" "false"' /usr/lib/sunshine-host/bin/run-rocknix.sh
	@grep -Fq 'game_session_begin "MORROWIND" "false"' /usr/lib/sunshine-host/bin/run-morrowind-openmw.sh
	@grep -Fq -- '--app-id=game-session-controller-required' /usr/lib/sunshine-host/bin/game-session.sh
	@grep -Fq -- '--app-id=game-session-error' /usr/lib/sunshine-host/bin/game-session.sh
	@grep -Fq 'for_window [app_id="^game-session-controller-required$$"] fullscreen enable' "$(CONFIG_DIR)/sway/sway.conf"
	@grep -Fq 'for_window [app_id="^game-session-error$$"] fullscreen enable' "$(CONFIG_DIR)/sway/sway.conf"
	@cmp -s "$(QUAKE3_AUTOEXEC_SOURCE)" "$(QUAKE3_AUTOEXEC_INSTALLED)"
	@test "$$(stat -c '%U:%G:%a' "$(QUAKE3_AUTOEXEC_INSTALLED)")" = system:system:600
	@command -v steam >/dev/null
	@command -v firefox >/dev/null
	@command -v docker >/dev/null
	@test "$$(systemctl is-enabled docker.service)" = enabled
	@test "$$(systemctl is-active docker.service)" = active
	@id -nG system | tr ' ' '\n' | grep -Fxq docker
	@grep -Fq '/mnt/iceburg/roms:/storage/roms:rw' /usr/lib/sunshine-host/bin/run-rocknix.sh
	@grep -Fq '/opt/games/rocknix/current/rootfs/usr/lib/libretro:/tmp/cores:ro' /usr/lib/sunshine-host/bin/run-rocknix.sh
	@grep -Fq '/var/lib/sunshine-host/games/rocknix/joypads:/tmp/joypads:ro' /usr/lib/sunshine-host/bin/run-rocknix.sh
	@grep -Fq -- '--cap-drop ALL' /usr/lib/sunshine-host/bin/run-rocknix.sh
	@! grep -Fq -- '--privileged' /usr/lib/sunshine-host/bin/run-rocknix.sh
	@test -s "$(STATE_DIR)/games/rocknix/joypads/sunshine-retroarch.cfg"
	@test "$$(stat -c '%U:%G:%a' "$(STATE_DIR)/games/rocknix/joypads/sunshine-retroarch.cfg")" = system:system:600
	@! grep -Eq 'openmw-portmaster|Morrowind\.sh' /usr/lib/sunshine-host/bin/run-rocknix.sh
	@python3 -c 'import json; data = json.load(open("$(CONFIG_DIR)/apps.json", encoding="utf-8")); assert [app["name"] for app in data["apps"]] == ["philby", "camera", "morrowind", "quake3", "rocknix", "steam"]'
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

reboot:
	@bash ../../pane.sh sunshine-host-reboot $(MAKE) --no-print-directory reboot-apply

reboot-apply: preflight
	@grep -Fxq 'GRUB_CMDLINE_LINUX_DEFAULT="quiet amdgpu.runpm=0"' /etc/default/grub || { \
		echo "Holly's amdgpu.runpm=0 boot setting is not installed; run make setup first." >&2; exit 1; \
	}
	sudo systemctl reboot
