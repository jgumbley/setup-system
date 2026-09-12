SHELL := /bin/bash
.DEFAULT_GOAL := help

HOSTNAME := rocks
USER := system
USB_DEVICE := 06cb:00bd

.PHONY: help preflight configure configure-apply register register-apply reregister reregister-apply verify verify-apply check activate-lock activate-lock-apply lock lock-apply

help:
	@echo "Targets:"
	@echo "  make configure Apply host setup including Hyprlock authentication"
	@echo "  make register  Enrol a fingerprint for $(USER)"
	@echo "  make reregister Replace the enrolled right index fingerprint"
	@echo "  make verify    Verify the enrolled fingerprint interactively"
	@echo "  make check     Validate the managed lock configuration sources"
	@echo "  make activate-lock Restart the current Rocks idle manager"
	@echo "  make lock      Lock Rocks for an interactive unlock test"

configure:
	bash ../../pane.sh configure-fingerprint $(MAKE) configure-apply

configure-apply:
	$(MAKE) -C ../.. setup

preflight:
	@test "$$(hostname)" = "$(HOSTNAME)" || { echo "Fingerprint registration is only supported on $(HOSTNAME)." >&2; exit 1; }
	@test "$$(id -un)" = "$(USER)" || { echo "Run fingerprint registration as $(USER)." >&2; exit 1; }
	@lsusb -d "$(USB_DEVICE)" | grep -Fq "$(USB_DEVICE)" || { echo "Fingerprint reader $(USB_DEVICE) was not detected." >&2; exit 1; }
	@command -v fprintd-enroll >/dev/null || { echo "fprintd-enroll is unavailable; run make setup first." >&2; exit 1; }
	@command -v hyprlock >/dev/null || { echo "Hyprlock is unavailable; run make setup first." >&2; exit 1; }
	@test -f /etc/pam.d/hyprlock -a -f "$(HOME)/.config/hypr/hyprlock.conf" || { echo "Hyprlock is not configured; run make setup first." >&2; exit 1; }

register:
	bash ../../pane.sh register-fingerprint $(MAKE) register-apply

register-apply: preflight
	@! fprintd-list "$(USER)" | grep -Fq ' - #' || { echo "$(USER) already has an enrolled fingerprint; refusing to overwrite it." >&2; exit 1; }
	sudo fprintd-enroll "$(USER)"
	fprintd-list "$(USER)"

reregister:
	bash ../../pane.sh reregister-fingerprint $(MAKE) reregister-apply

reregister-apply: preflight
	sudo fprintd-enroll -f right-index-finger "$(USER)"
	fprintd-list "$(USER)"

verify:
	bash ../../pane.sh verify-fingerprint $(MAKE) verify-apply

verify-apply: preflight
	fprintd-verify "$(USER)"

check:
	@python3 -c 'import pathlib, subprocess, yaml; tasks = yaml.safe_load(pathlib.Path("../../roles/sway-desktop/tasks/main.yml").read_text()); block = next(t["block"] for t in tasks if t.get("name") == "Configure Rocks screen locking"); script = next(t["ansible.builtin.copy"]["content"] for t in block if t.get("name") == "Install Hyprlock launch and readiness helper"); subprocess.run(["bash", "-n"], input=script, text=True, check=True); yaml.safe_load(pathlib.Path("../../roles/sway-fpreader/tasks/main.yml").read_text())'
	@git diff --check -- ../../roles/sway-desktop ../../roles/sway-fpreader Makefile

activate-lock:
	bash ../../pane.sh activate-hyprlock $(MAKE) activate-lock-apply

activate-lock-apply: preflight
	@test -n "$(SWAYSOCK)" || { echo "Run inside Rocks Sway session." >&2; exit 1; }
	@test "$$(pgrep -c -u "$$(id -u)" -x swayidle)" = 1 || { echo "Expected one running swayidle process; nothing changed." >&2; exit 1; }
	@set -eu; command="$$(python3 -c 'import pathlib, re; text = pathlib.Path.home().joinpath(".config/sway/config").read_text(); match = re.search(r"^exec swayidle -w .*?(?<!\\)$$", text, re.M | re.S); assert match, "Missing managed swayidle command"; command = match[0].replace("\\\n", " "); assert "lock-screen" in command, "Hyprlock idle configuration is not installed"; print(command)')"; \
		pkill -u "$$(id -u)" -x swayidle; \
		swaymsg -s "$(SWAYSOCK)" "$$command"
	@sleep 1
	@test "$$(pgrep -c -u "$$(id -u)" -x swayidle)" = 1
	@pgrep -a -u "$$(id -u)" -x swayidle

lock:
	bash ../../pane.sh test-hyprlock $(MAKE) lock-apply

lock-apply: preflight
	@"$(HOME)/.local/bin/lock-screen"
