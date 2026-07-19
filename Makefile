.DEFAULT_GOAL := help

.PHONY: help
help:
	@echo "Targets:"
	@echo "  make updates        Refresh coding agents (sudo/become prompts)"
	@echo "  make term           Configure terminal environment"
	@echo "  make setup          Full machine setup "
	@echo "  make vnc-viewer     Install the TigerVNC viewer"
	@echo "  make nas            Mount NAS via Ansible playbook"
	@echo "  make backup         Backup ~/wip and HAL's Sunshine pairing state to NAS"
	@echo "  make android-usb    Format a 64 GB Lexar USB stick for Android"

include common.mk

HOSTNAME := $(shell hostname)
BACKUP_ROOT := /usr/local/mnt/iceburg/backup/$(HOSTNAME).smeg
SUNSHINE_STATE_DIR := /var/lib/sunshine-host
SUNSHINE_BACKUP_DIR := $(BACKUP_ROOT)/sunshine
SUNSHINE_BACKUP_FILES := sunshine_state.json cakey.pem cacert.pem

.PHONY: term updates nas setup vnc-viewer vnc-viewer-apply check backup caffeinate android-usb android-usb-inspect

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

check:
	ansible-playbook setup.yml -c local --syntax-check

backup: nas
	@echo "Backing up to $(BACKUP_ROOT)/wip"
	mkdir -p "$(BACKUP_ROOT)/wip"
	rsync -rlptDvz --progress --update --no-group \
		--exclude='node_modules' \
		--exclude='__pycache__' \
		--exclude='.DS_Store' \
		--exclude='venv' \
		--exclude='.venv' \
		--exclude='.uv-cache' \
		--exclude='/platform/sunshine-host/.runtime/' \
		--exclude='/platform/sunshine-host/.state/' \
		~/wip/ "$(BACKUP_ROOT)/wip/"
	@if [ "$(HOSTNAME)" = hal ]; then \
		for state_file in $(SUNSHINE_BACKUP_FILES); do \
			test -f "$(SUNSHINE_STATE_DIR)/$$state_file" || { echo "Missing Sunshine pairing state: $(SUNSHINE_STATE_DIR)/$$state_file" >&2; exit 1; }; \
		done; \
		echo "Backing up Sunshine pairing state to $(SUNSHINE_BACKUP_DIR)"; \
		mkdir -p "$(SUNSHINE_BACKUP_DIR)"; \
		chmod 700 "$(SUNSHINE_BACKUP_DIR)"; \
		rsync -rlptDv --progress --checksum --no-group --chmod=D700,F600 \
			$(foreach state_file,$(SUNSHINE_BACKUP_FILES),"$(SUNSHINE_STATE_DIR)/$(state_file)") \
			"$(SUNSHINE_BACKUP_DIR)/"; \
	fi

caffeinate:
	sudo systemd-inhibit --what=sleep:idle:handle-lid-switch --who="Make Caffeinate" --why="Preventing system sleep and suspend" --mode=block sleep infinity

android-usb-inspect:
	$(MAKE) -C utils/format_android_usb inspect DEVICE=$(DEVICE)

android-usb:
	$(MAKE) -C utils/format_android_usb format DEVICE=$(DEVICE) CONFIRM=$(CONFIRM)
