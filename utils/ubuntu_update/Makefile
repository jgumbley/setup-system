SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

.PHONY: help preflight check update update-apply verify

help:
	@echo "make check   Show Ubuntu version, package health and available updates (cached APT lists)"
	@echo "make update  Refresh APT and update Ubuntu 26.04 packages in a tmux pane"
	@echo "make verify  Verify Ubuntu 26.04.1 or later within 26.04 after reboot"

preflight:
	@. /etc/os-release; \
		test "$$ID" = ubuntu && test "$$VERSION_ID" = 26.04 || { echo "This utility requires Ubuntu 26.04." >&2; exit 1; }
	@audit="$$(dpkg --audit)"; \
		test -z "$$audit" || { printf '%s\n' "$$audit" >&2; exit 1; }

check: preflight
	@. /etc/os-release; printf 'OS: %s\n' "$$PRETTY_NAME"
	@printf 'Running kernel: '; uname -r
	@echo "Held packages:"
	@apt-mark showhold
	@echo "Update preview using cached APT lists; make update refreshes them first:"
	@LC_ALL=C apt-get --simulate dist-upgrade
	@if test -e /run/reboot-required; then echo "Reboot required."; else echo "No pending reboot reported."; fi

update:
	bash ../../pane.sh ubuntu-update $(MAKE) --no-print-directory update-apply

# Internal target: update starts this inside pane.sh for APT and sudo prompts.
update-apply: preflight
	sudo apt-get --error-on=any update
	sudo apt-get dist-upgrade
	@echo "Package update finished. Reboot, then run make -C utils/ubuntu_update verify from the repository root."

verify: preflight
	@. /etc/os-release; \
		dpkg --compare-versions "$${VERSION%% *}" ge 26.04.1 || { echo "Ubuntu 26.04.1 package baseline has not been reached." >&2; exit 1; }; \
		printf 'OS: %s\n' "$$PRETTY_NAME"
	@printf 'Running kernel: '; uname -r
	@test ! -e /run/reboot-required || { echo "Reboot is still required." >&2; exit 1; }
	@simulation="$$(LC_ALL=C apt-get --simulate dist-upgrade)"; \
		printf '%s\n' "$$simulation"; \
		if grep -Eq '^(Inst|Remv|Conf) ' <<< "$$simulation"; then \
			echo "APT still proposes package changes; run make check to inspect them." >&2; exit 1; \
		fi
	@echo "Ubuntu package verification passed using the current APT lists."
