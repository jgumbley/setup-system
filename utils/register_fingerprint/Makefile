SHELL := /bin/bash
.DEFAULT_GOAL := help

HOSTNAME := rocks
USER := system
USB_DEVICE := 06cb:00bd

.PHONY: help preflight register verify

help:
	@echo "Targets:"
	@echo "  make register  Enrol a fingerprint for $(USER)"
	@echo "  make verify    Verify the enrolled fingerprint interactively"

preflight:
	@test "$$(hostname)" = "$(HOSTNAME)" || { echo "Fingerprint registration is only supported on $(HOSTNAME)." >&2; exit 1; }
	@test "$$(id -un)" = "$(USER)" || { echo "Run fingerprint registration as $(USER)." >&2; exit 1; }
	@lsusb -d "$(USB_DEVICE)" | grep -Fq "$(USB_DEVICE)" || { echo "Fingerprint reader $(USB_DEVICE) was not detected." >&2; exit 1; }
	@command -v fprintd-enroll >/dev/null || { echo "fprintd-enroll is unavailable; run make setup first." >&2; exit 1; }
	@grep -Fq pam_fprintd.so /etc/pam.d/common-auth || { echo "Fingerprint PAM authentication is disabled; run make setup first." >&2; exit 1; }

register: preflight
	@! fprintd-list "$(USER)" | grep -Fq ' - #' || { echo "$(USER) already has an enrolled fingerprint; refusing to overwrite it." >&2; exit 1; }
	sudo fprintd-enroll "$(USER)"
	fprintd-list "$(USER)"

verify: preflight
	fprintd-verify "$(USER)"
