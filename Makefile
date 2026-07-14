.DEFAULT_GOAL := help

.PHONY: help
help:
	@echo "Targets:"
	@echo "  make updates        Refresh coding agents (sudo/become prompts)"
	@echo "  make term           Configure terminal environment"
	@echo "  make setup          Full machine setup "
	@echo "  make vnc-viewer     Install the TigerVNC viewer"
	@echo "  make sunshine-host Install the native Sunshine host package on HAL"
	@echo "  make nas            Mount NAS via Ansible playbook"
	@echo "  make backup         Backup ~/wip to NAS (mounts first)"
	@echo "  make android-usb    Format a 64 GB Lexar USB stick for Android"

include common.mk

HOSTNAME := $(shell hostname)

.PHONY: term updates nas setup vnc-viewer vnc-viewer-apply sunshine-host sunshine-host-apply check backup caffeinate android-usb android-usb-inspect

.bootstrapped:
ifeq ($(shell uname -s),Darwin)
	su admin -c "cd $(PWD) && ./bootstrap/darwin.sh" && touch .bootstrapped
else
	./bootstrap/ubuntu.sh && touch .bootstrapped
endif

updates: .bootstrapped
ifeq ($(shell uname -s),Darwin)
	su admin -c "cd $(PWD) && ANSIBLE_REMOTE_TMP=/tmp ansible-playbook updates.yml -c local --ask-become-pass"
else
	ansible-playbook updates.yml -c local -K
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
ifeq ($(shell uname -s),Darwin)
	su admin -c "cd $(PWD) && ANSIBLE_REMOTE_TMP=/tmp ansible-playbook setup.yml -c local --ask-become-pass"
else
	ansible-playbook setup.yml -c local -K
endif

vnc-viewer:
	bash pane.sh install-vnc-viewer $(MAKE) vnc-viewer-apply

vnc-viewer-apply: .bootstrapped
	ansible-playbook setup.yml -c local -K --tags vnc-viewer

sunshine-host: .bootstrapped
	bash pane.sh sunshine-host $(MAKE) --no-print-directory sunshine-host-apply

sunshine-host-apply:
	ansible-playbook sunshine-host.yml -c local -K

check:
	ansible-playbook setup.yml -c local --syntax-check
	ansible-playbook sunshine-host.yml -c local --syntax-check

backup: nas
	@echo "Backing up to /usr/local/mnt/iceburg/backup/$(HOSTNAME).smeg/wip"
	mkdir -p /usr/local/mnt/iceburg/backup/$(HOSTNAME).smeg/wip
	rsync -rlptDvz --progress --update --no-group --exclude='node_modules' --exclude='__pycache__' --exclude='.DS_Store' --exclude='venv' --exclude='.venv' --exclude='.uv-cache' ~/wip/ /usr/local/mnt/iceburg/backup/$(HOSTNAME).smeg/wip/

caffeinate:
	sudo systemd-inhibit --what=sleep:idle:handle-lid-switch --who="Make Caffeinate" --why="Preventing system sleep and suspend" --mode=block sleep infinity

android-usb-inspect:
	$(MAKE) -C utils/format_android_usb inspect DEVICE=$(DEVICE)

android-usb:
	$(MAKE) -C utils/format_android_usb format DEVICE=$(DEVICE) CONFIRM=$(CONFIRM)
