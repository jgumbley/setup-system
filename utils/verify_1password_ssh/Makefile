.DEFAULT_GOAL := help

.PHONY: help verify

help:
	@echo "Targets:"
	@echo "  make verify  Check the desktop SSH agent and loaded keys"

verify:
	@command -v 1password >/dev/null || { echo "1Password desktop app is not installed." >&2; exit 1; }
	@pgrep -x 1password >/dev/null || { echo "1Password desktop app is not running. Open and unlock it, then retry." >&2; exit 1; }
	@test -S "$(HOME)/.1password/agent.sock" || { echo "1Password SSH agent socket is unavailable. In 1Password, enable Settings > Developer > Use the SSH agent, then unlock the app and retry." >&2; exit 1; }
	@SSH_AUTH_SOCK="$(HOME)/.1password/agent.sock" ssh-add -l >/dev/null 2>&1 || { echo "1Password SSH agent has no available keys. Add or import an SSH Key item in an unlocked vault, then retry." >&2; exit 1; }
	@echo "1Password SSH agent is running and has at least one available key."
