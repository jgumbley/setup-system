.DEFAULT_GOAL := help

.PHONY: help verify verify-holly

help:
	@echo "Targets:"
	@echo "  make verify  Check the desktop SSH agent and loaded keys"
	@echo "  make verify-holly  Check forwarded 1Password access and a Git push from Holly"

verify:
	@command -v 1password >/dev/null || { echo "1Password desktop app is not installed." >&2; exit 1; }
	@pgrep -x 1password >/dev/null || { echo "1Password desktop app is not running. Open and unlock it, then retry." >&2; exit 1; }
	@test -S "$(HOME)/.1password/agent.sock" || { echo "1Password SSH agent socket is unavailable. In 1Password, enable Settings > Developer > Use the SSH agent, then unlock the app and retry." >&2; exit 1; }
	@SSH_AUTH_SOCK="$(HOME)/.1password/agent.sock" ssh-add -l >/dev/null 2>&1 || { echo "1Password SSH agent has no available keys. Add or import an SSH Key item in an unlocked vault, then retry." >&2; exit 1; }
	@echo "1Password SSH agent is running and has at least one available key."

verify-holly: verify
	@ssh -G holly.smeg | grep -Fxq "forwardagent $(HOME)/.1password/agent.sock" || { echo "Holly must forward the 1Password socket; apply the terminal role with make setup." >&2; exit 1; }
	@ssh -o BatchMode=yes -o StrictHostKeyChecking=yes system@holly.smeg 'cd /home/system/wip/setup-system && test -S "$$SSH_AUTH_SOCK" && ssh-add -l >/dev/null && test "$$(git remote get-url --push origin)" = git@github.com:jgumbley/setup-system.git && GIT_SSH_COMMAND="ssh -o BatchMode=yes -o StrictHostKeyChecking=yes" git push --dry-run origin main'
