.DEFAULT_GOAL := help

.PHONY: help
help:
	@echo "Targets:"
	@echo "  make core           Run core system setup (sudo/BEcome prompts)"
	@echo "  make term           Configure terminal environment"
	@echo "  make setup          Full machine setup (Linux)"
	@echo "  make nas            Mount NAS via Ansible playbook"
	@echo "  make backup         Backup ~/wip to NAS (mounts first)"
	@echo "  make agent-core     Run 'make core' in a tmux agent pane"
	@echo "  make agent-<target> Run any target in a tmux agent pane"

include common.mk

HOSTNAME := $(shell hostname)

.PHONY: cross-platform linux mac config push term core-tools nas setup backup inference status caffeinate agent agent-core agent-setup

# Allow invoking any Make target inside the tmux agent helper.
AGENT_TARGET := $(if $(TARGET),$(TARGET),$(target))

.bootstrapped:
ifeq ($(shell uname -s),Darwin)
	su admin -c "cd $(PWD) && ./bootstrap/darwin.sh" && touch .bootstrapped
else
	sudo ./bootstrap/ubuntu.sh && touch .bootstrapped
endif

core: .bootstrapped
ifeq ($(shell uname -s),Darwin)
	su admin -c "cd $(PWD) && ANSIBLE_REMOTE_TMP=/tmp ansible-playbook core.yml -c local --ask-become-pass"
else
	ansible-playbook core.yml -c local -K
endif

nas: .bootstrapped
ifeq ($(shell uname -s),Darwin)
	cd $(PWD) && ANSIBLE_REMOTE_TMP=/tmp ansible-playbook nas.yml -c local -b
else
	ansible-playbook nas.yml -c local -K
endif

term:
	ansible-playbook terminal.yml

setup: .bootstrapped
	ansible-playbook setup.yml -c local -K

claude:
	sudo -E claude

backup:
	$(MAKE) nas
	@echo "Backing up to /usr/local/mnt/iceburg/backup/$(HOSTNAME).smeg/wip"
	mkdir -p /usr/local/mnt/iceburg/backup/$(HOSTNAME).smeg/wip
	rsync -rlptDvz --progress --update --no-group --exclude='node_modules' --exclude='__pycache__' --exclude='.DS_Store' --exclude='venv' --exclude='.venv' ~/wip/ /usr/local/mnt/iceburg/backup/$(HOSTNAME).smeg/wip/

caffeinate:
	sudo systemd-inhibit --what=sleep:idle:handle-lid-switch --who="Make Caffeinate" --why="Preventing system sleep and suspend" --mode=block sleep infinity

agent:
	@if [ -z "$(AGENT_TARGET)" ]; then \
		echo "Usage: make agent TARGET=<make-target>"; \
		exit 1; \
	fi
	@bash scripts/run-in-agent-pane.sh agent-$(AGENT_TARGET) $(MAKE) $(AGENT_TARGET)

agent-core:
	@$(MAKE) agent TARGET=core

agent-setup:
	@$(MAKE) agent TARGET=setup
