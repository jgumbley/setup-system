SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

BACKUP_ROOT := /usr/local/mnt/iceburg/backup
STATUS_SCRIPT := $(CURDIR)/backup_status.py

.PHONY: help check status record

help:
	@echo "Targets:"
	@echo "  make status  Show the last successful backup date for each host"
	@echo "  make check   Test the backup status utility"

check:
	python3 -B -m unittest -v

status:
	@python3 -B "$(STATUS_SCRIPT)" status "$(BACKUP_ROOT)"

record:
	@test -n "$(BACKUP_PATH)" || { echo "BACKUP_PATH is required" >&2; exit 2; }
	@python3 -B "$(STATUS_SCRIPT)" record "$(BACKUP_PATH)"
