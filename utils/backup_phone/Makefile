SHELL := /bin/bash
.DEFAULT_GOAL := help

PHONE_HOSTNAME := pixel-phone-rooted
REPO_ROOT := ../..

.PHONY: help backup backup-apply

help:
	@echo "Targets:"
	@echo "  make backup  Mount the NAS and back up the rooted phone filesystem"

backup:
	bash ../../pane.sh backup-phone $(MAKE) backup-apply

backup-apply:
	$(MAKE) -C $(REPO_ROOT) nas
	mkdir -p /usr/local/mnt/iceburg/backup/$(PHONE_HOSTNAME).smeg/wip
	adb start-server
	adb wait-for-device
	adb root
	adb wait-for-device
	adb pull / /usr/local/mnt/iceburg/backup/$(PHONE_HOSTNAME).smeg/wip/
