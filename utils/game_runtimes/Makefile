SHELL := /bin/bash
.DEFAULT_GOAL := help

PYTHON ?= python3
SCRIPT := game_runtimes.py
MANIFEST := manifest.json
PANE := ../../pane.sh

.PHONY: help check status verify \
	status-quake3 verify-quake3 status-rocknix verify-rocknix \
	import-content import-content-apply import-state import-state-apply \
	build build-apply build-openmw build-openmw-apply \
	build-quake3 build-quake3-apply build-rocknix build-rocknix-apply \
	clean-rocknix-cache clean-rocknix-cache-apply \
	backup-state backup-state-locked-apply backup-state-apply \
	restore-state restore-state-locked-apply restore-state-apply

help:
	@echo 'Game runtime lifecycle utility (Holly only)'
	@echo '  make check'
	@echo 'Quake III operator workflow:'
	@echo '  1. make build-quake3'
	@echo '  2. make verify-quake3'
	@echo '  PK3 content is externally managed under the canonical ROMs tree.'
	@echo '  make status-quake3'
	@echo 'ROCKNIX operator workflow:'
	@echo '  1. make build-rocknix'
	@echo '  2. make verify-rocknix'
	@echo '  ROM content is mounted from /mnt/iceburg/roms.'
	@echo '  make status-rocknix'
	@echo '  make clean-rocknix-cache  Remove only generated ROCKNIX source/build cache'
	@echo 'Aggregate lifecycle (not required by the Quake-only workflow):'
	@echo '  make status'
	@echo '  make import-content'
	@echo '  make import-state'
	@echo '  make build-openmw'
	@echo '  make build-rocknix'
	@echo '  make build'
	@echo '  make verify'
	@echo '  make backup-state'
	@echo '  make restore-state SNAPSHOT=<UTC snapshot> COMPONENT=<morrowind|quake3|rocknix> CONFIRM_HOST=holly'

check:
	@$(PYTHON) -B $(SCRIPT) --manifest $(MANIFEST) self-test
	@git diff --check -- .

status:
	@$(PYTHON) -B $(SCRIPT) --manifest $(MANIFEST) status

verify:
	@$(PYTHON) -B $(SCRIPT) --manifest $(MANIFEST) verify

status-quake3:
	@$(PYTHON) -B $(SCRIPT) --manifest $(MANIFEST) status-quake3

verify-quake3:
	@$(PYTHON) -B $(SCRIPT) --manifest $(MANIFEST) verify-quake3

status-rocknix:
	@$(PYTHON) -B $(SCRIPT) --manifest $(MANIFEST) status-rocknix

verify-rocknix:
	@$(PYTHON) -B $(SCRIPT) --manifest $(MANIFEST) verify-rocknix

import-content:
	@bash $(PANE) game-runtimes-import-content $(MAKE) --no-print-directory -C '$(CURDIR)' import-content-apply

import-content-apply:
	@sudo $(PYTHON) -B $(SCRIPT) --manifest $(MANIFEST) import-content

import-state:
	@bash $(PANE) game-runtimes-import-state $(MAKE) --no-print-directory -C '$(CURDIR)' import-state-apply

import-state-apply:
	@sudo $(PYTHON) -B $(SCRIPT) --manifest $(MANIFEST) import-state

build-openmw:
	@bash $(PANE) game-runtimes-build-openmw $(MAKE) --no-print-directory -C '$(CURDIR)' build-openmw-apply

build-openmw-apply:
	@sudo $(PYTHON) -B $(SCRIPT) --manifest $(MANIFEST) build-openmw

build-quake3:
	@bash $(PANE) game-runtimes-build-quake3 $(MAKE) --no-print-directory -C '$(CURDIR)' build-quake3-apply

build-quake3-apply:
	@sudo $(PYTHON) -B $(SCRIPT) --manifest $(MANIFEST) build-quake3

build-rocknix:
	@bash $(PANE) game-runtimes-build-rocknix $(MAKE) --no-print-directory -C '$(CURDIR)' build-rocknix-apply

build-rocknix-apply:
	@sudo $(PYTHON) -B $(SCRIPT) --manifest $(MANIFEST) build-rocknix

clean-rocknix-cache:
	@bash $(PANE) game-runtimes-clean-rocknix-cache $(MAKE) --no-print-directory -C '$(CURDIR)' clean-rocknix-cache-apply

clean-rocknix-cache-apply:
	@sudo $(PYTHON) -B $(SCRIPT) --manifest $(MANIFEST) clean-rocknix-cache

build:
	@bash $(PANE) game-runtimes-build-all $(MAKE) --no-print-directory -C '$(CURDIR)' build-apply

build-apply:
	@sudo $(PYTHON) -B $(SCRIPT) --manifest $(MANIFEST) build-all

backup-state:
	@bash $(PANE) game-runtimes-backup-state $(MAKE) --no-print-directory -C '$(CURDIR)' backup-state-locked-apply

backup-state-locked-apply:
	@sudo install -d -m 0755 /run/sunshine-host
	@sudo flock -x /run/lock/setup-system-backup.lock flock -x /run/sunshine-host/game-session.lock \
		$(MAKE) --no-print-directory -C '$(CURDIR)' backup-state-apply

# Root make backup already holds both locks before invoking this target.
backup-state-apply:
	@$(PYTHON) -B $(SCRIPT) --manifest $(MANIFEST) backup-state

restore-state:
	@$(PYTHON) -B $(SCRIPT) --manifest $(MANIFEST) validate-restore \
		--snapshot '$(SNAPSHOT)' --component '$(COMPONENT)' --confirm-host '$(CONFIRM_HOST)'
	@bash $(PANE) game-runtimes-restore-state $(MAKE) --no-print-directory -C '$(CURDIR)' \
		restore-state-locked-apply SNAPSHOT='$(SNAPSHOT)' COMPONENT='$(COMPONENT)' CONFIRM_HOST='$(CONFIRM_HOST)'

restore-state-locked-apply:
	@sudo install -d -m 0755 /run/sunshine-host
	@sudo flock -x /run/lock/setup-system-backup.lock flock -x /run/sunshine-host/game-session.lock \
		$(MAKE) --no-print-directory -C '$(CURDIR)' restore-state-apply \
		SNAPSHOT='$(SNAPSHOT)' COMPONENT='$(COMPONENT)' CONFIRM_HOST='$(CONFIRM_HOST)'

restore-state-apply:
	@$(PYTHON) -B $(SCRIPT) --manifest $(MANIFEST) restore-state \
		--snapshot '$(SNAPSHOT)' --component '$(COMPONENT)' --confirm-host '$(CONFIRM_HOST)'
