.DEFAULT_GOAL := help

.PHONY: help
help:
	@echo "Targets:"
	@echo "  make core           Run core system setup (sudo/BEcome prompts)"
	@echo "  make term           Configure terminal environment"
	@echo "  make setup          Full machine setup (Linux)"
	@echo "  make nas            Mount NAS via Ansible playbook"
	@echo "  make backup         Backup ~/wip to NAS (mounts first)"

include common.mk

HOSTNAME := $(shell hostname)

.PHONY: term core nas setup backup caffeinate 

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

backup:
	$(MAKE) nas
	@echo "Backing up to /usr/local/mnt/iceburg/backup/$(HOSTNAME).smeg/wip"
	mkdir -p /usr/local/mnt/iceburg/backup/$(HOSTNAME).smeg/wip
	rsync -rlptDvz --progress --update --no-group --exclude='node_modules' --exclude='__pycache__' --exclude='.DS_Store' --exclude='venv' --exclude='.venv' ~/wip/ /usr/local/mnt/iceburg/backup/$(HOSTNAME).smeg/wip/

caffeinate:
	sudo systemd-inhibit --what=sleep:idle:handle-lid-switch --who="Make Caffeinate" --why="Preventing system sleep and suspend" --mode=block sleep infinity
