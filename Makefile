.DEFAULT_GOAL := help

.PHONY: help
help:
	@echo "Targets:"
	@echo "  make updates        Refresh shared tools and essentials (sudo/become prompts)"
	@echo "  make term           Configure terminal environment"
	@echo "  make setup          Full machine setup "
	@echo "  make nas            Mount NAS via Ansible playbook"
	@echo "  make backup         Backup ~/wip to NAS (mounts first)"
	@echo "  make backup-phone   Backup rooted phone filesystem to NAS (mounts first)"
	@echo "  make moonlight      Install Moonlight streaming client (snap, sudo prompt)"
	@echo "  make prep-rpi-sd DEVICE=/dev/sdX CONFIRM=legobrick"
	@echo "  make commission-legobrick"
	@echo "  make setup-legobrick"
	@echo "  make verify-legobrick"
	@echo "  make prep-ubuntu-usb DEVICE=/dev/sdX CONFIRM=rocks"

include common.mk

HOSTNAME := $(shell hostname)
PHONE_HOSTNAME := pixel-phone-rooted

.PHONY: term updates nas setup backup backup-phone caffeinate moonlight prep-rpi-sd commission-legobrick setup-legobrick verify-legobrick prep-ubuntu-usb

prep-rpi-sd:
	bash pane.sh prep-legobrick-sd $(MAKE) -C utils/prep_rpi_sd prepare DEVICE=$(DEVICE) CONFIRM=$(CONFIRM)

commission-legobrick:
	bash pane.sh commission-legobrick $(MAKE) -C utils/prep_rpi_sd commission

setup-legobrick:
	bash pane.sh setup-legobrick $(MAKE) -C utils/prep_rpi_sd setup

verify-legobrick:
	bash pane.sh verify-legobrick $(MAKE) -C utils/prep_rpi_sd verify

prep-ubuntu-usb:
	bash pane.sh prep-rocks-usb $(MAKE) -C utils/prep_ubuntu_usb prepare DEVICE=$(DEVICE) CONFIRM=$(CONFIRM)

moonlight:
	ansible-playbook moonlight.yml -c local -K

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
	su admin -c "cd $(PWD) && ANSIBLE_REMOTE_TMP=/tmp ansible-playbook updates.yml setup.yml -c local --ask-become-pass"
else
	ansible-playbook updates.yml setup.yml -c local -K
endif

backup: nas
	@echo "Backing up to /usr/local/mnt/iceburg/backup/$(HOSTNAME).smeg/wip"
	mkdir -p /usr/local/mnt/iceburg/backup/$(HOSTNAME).smeg/wip
	rsync -rlptDvz --progress --update --no-group --exclude='node_modules' --exclude='__pycache__' --exclude='.DS_Store' --exclude='venv' --exclude='.venv' ~/wip/ /usr/local/mnt/iceburg/backup/$(HOSTNAME).smeg/wip/

backup-phone: nas
	mkdir -p /usr/local/mnt/iceburg/backup/$(PHONE_HOSTNAME).smeg/wip
	adb start-server
	adb wait-for-device
	adb root
	adb wait-for-device
	adb pull / /usr/local/mnt/iceburg/backup/$(PHONE_HOSTNAME).smeg/wip/

caffeinate:
	sudo systemd-inhibit --what=sleep:idle:handle-lid-switch --who="Make Caffeinate" --why="Preventing system sleep and suspend" --mode=block sleep infinity
