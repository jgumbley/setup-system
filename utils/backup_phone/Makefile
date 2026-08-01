SHELL := /bin/bash
.DEFAULT_GOAL := help

PHONE_HOSTNAME := pixel-phone-rooted
REPO_ROOT := ../..
BACKUP_ROOT := /usr/local/mnt/iceburg/backup/$(PHONE_HOSTNAME).smeg

.PHONY: help backup backup-apply

help:
	@echo "Targets:"
	@echo "  make backup  Mount the NAS and back up the rooted phone filesystem"

backup:
	bash ../../pane.sh backup-phone $(MAKE) backup-apply

backup-apply:
	$(MAKE) -C $(REPO_ROOT) nas
	mkdir -p "$(BACKUP_ROOT)/wip"
	adb start-server
	adb wait-for-device
	adb root
	adb wait-for-device
	adb pull / "$(BACKUP_ROOT)/wip/"
	$(MAKE) -C ../backup_status --no-print-directory record BACKUP_PATH="$(BACKUP_ROOT)"
