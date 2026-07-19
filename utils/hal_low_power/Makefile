SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

HOSTNAME := hal
WIRED_INTERFACE := enp10s0
WIFI_INTERFACE := wlp9s0
GPU_BDF := 0000:03:00.0
GPU_DEVICE := /sys/bus/pci/devices/$(GPU_BDF)
SUNSHINE_UNITS := sunshine-host.target sunshine-host-sunshine.service sunshine-host-sway.service
STOPPED_UNITS := $(SUNSHINE_UNITS) gdm.service seatd.service power-profiles-daemon.service

.PHONY: help preflight inspect fan-inspect fan-inspect-apply apply apply-apply verify

help:
	@echo "Targets:"
	@echo "  make inspect      Show HAL's current runtime power state"
	@echo "  make fan-inspect  Load the temporary board-sensor driver and show fan controls"
	@echo "  make apply        Minimize HAL power use until its next reboot"

preflight:
	@test "$$(hostname)" = "$(HOSTNAME)" || { echo "This utility only supports $(HOSTNAME)." >&2; exit 1; }
	@test -n "$${SSH_CONNECTION:-}" || { echo "Run this utility from an SSH session." >&2; exit 1; }
	@client="$${SSH_CONNECTION%% *}"; ip route get "$$client" | grep -Eq '(^| )dev $(WIRED_INTERFACE)( |$$)' || { echo "The SSH session is not using $(WIRED_INTERFACE)." >&2; exit 1; }
	@test "$$(cat /sys/devices/system/cpu/cpufreq/policy0/scaling_driver)" = amd-pstate-epp || { echo "HAL is not using amd-pstate-epp." >&2; exit 1; }
	@test "$$(cat $(GPU_DEVICE)/vendor)" = 0x1002 || { echo "Expected AMD GPU $(GPU_BDF) was not found." >&2; exit 1; }
	@test "$$(cat $(GPU_DEVICE)/device)" = 0x744c || { echo "Expected RX 7900 XTX $(GPU_BDF) was not found." >&2; exit 1; }
	@! grep -q '^connected$$' /sys/class/drm/card[0-9]-*/status || { echo "A display is connected; refusing to stop HAL's graphics stack." >&2; exit 1; }
	@test "$$(iw dev $(WIFI_INTERFACE) info | awk '$$1 == "type" { print $$2 }')" = monitor || { echo "$(WIFI_INTERFACE) is not in its expected monitor mode." >&2; exit 1; }
	@systemctl is-active --quiet wlp9s0-monitor.service || { echo "$(WIFI_INTERFACE)'s monitor-mode service is not active." >&2; exit 1; }
	@systemctl is-active --quiet open-creel-zeek.service || { echo "Zeek is not active on $(WIFI_INTERFACE)." >&2; exit 1; }

inspect:
	@systemctl show $(STOPPED_UNITS) -p Id -p LoadState -p ActiveState -p SubState -p UnitFileState
	@grep -H . /sys/devices/system/cpu/cpufreq/boost /sys/devices/system/cpu/cpufreq/policy0/scaling_governor /sys/devices/system/cpu/cpufreq/policy0/energy_performance_preference /sys/devices/system/cpu/cpufreq/policy0/scaling_min_freq /sys/devices/system/cpu/cpufreq/policy0/scaling_max_freq
	@grep -H . $(GPU_DEVICE)/power_dpm_force_performance_level $(GPU_DEVICE)/hwmon/hwmon*/power1_average
	@iw dev $(WIFI_INTERFACE) info | sed -n '/Interface /p; /type /p'

fan-inspect: preflight
	bash ../../pane.sh hal-fan-inspect $(MAKE) --no-print-directory fan-inspect-apply

fan-inspect-apply: preflight
	@sudo modprobe nct6683; trap 'sudo modprobe -r nct6683' EXIT; mapfile -t names < <(grep -l -E '^nct668[367]$$' /sys/class/hwmon/hwmon*/name); test "$${#names[@]}" -eq 1 || { echo "Expected one Nuvoton fan controller, found $${#names[@]}." >&2; exit 1; }; hwmon="$$(dirname "$${names[0]}")"; grep -H . "$$hwmon"/name "$$hwmon"/fan*_input "$$hwmon"/pwm*; stat -c '%A %U:%G %n' "$$hwmon"/pwm*

apply: preflight
	bash ../../pane.sh hal-low-power $(MAKE) --no-print-directory apply-apply

apply-apply: preflight
	sudo systemctl stop sunshine-host.target
	sudo systemctl stop sunshine-host-sunshine.service
	sudo systemctl stop sunshine-host-sway.service
	sudo systemctl stop gdm.service
	sudo systemctl stop seatd.service
	sudo systemctl stop power-profiles-daemon.service
	sudo systemctl reset-failed sunshine-host-sunshine.service sunshine-host-sway.service
	@! sudo fuser /dev/dri/card0 /dev/dri/renderD128 || { echo "The GPU is still in use; refusing to change its power level." >&2; exit 1; }
	@for policy in /sys/devices/system/cpu/cpufreq/policy*; do printf '%s\n' powersave | sudo tee "$$policy/scaling_governor" >/dev/null; printf '%s\n' power | sudo tee "$$policy/energy_performance_preference" >/dev/null; done
	@printf '%s\n' 0 | sudo tee /sys/devices/system/cpu/cpufreq/boost >/dev/null
	@printf '%s\n' low | sudo tee $(GPU_DEVICE)/power_dpm_force_performance_level >/dev/null
	$(MAKE) --no-print-directory verify

verify: preflight
	@for unit in $(STOPPED_UNITS); do ! systemctl is-active --quiet "$$unit" || { echo "$$unit is still active." >&2; exit 1; }; done
	@for policy in /sys/devices/system/cpu/cpufreq/policy*; do test "$$(<"$$policy/scaling_governor")" = powersave; test "$$(<"$$policy/energy_performance_preference")" = power; done
	@test "$$(cat /sys/devices/system/cpu/cpufreq/boost)" = 0
	@test "$$(cat $(GPU_DEVICE)/power_dpm_force_performance_level)" = low
	@test "$$(iw dev $(WIFI_INTERFACE) info | awk '$$1 == "type" { print $$2 }')" = monitor
	@systemctl is-active --quiet wlp9s0-monitor.service
	@systemctl is-active --quiet open-creel-zeek.service
	$(MAKE) --no-print-directory inspect
