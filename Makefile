HOSTNAME := $(shell hostname)

.PHONY: cross-platform linux mac config push term core-tools backup

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

term:
	ansible-playbook terminal.yml

setup: .bootstrapped
	ansible-playbook setup.yml -c local -K

backup:
	@echo "Backing up to /usr/local/mnt/iceburg/backup/$(HOSTNAME).smeg/wip"
	mkdir -p /usr/local/mnt/iceburg/backup/$(HOSTNAME).smeg/wip
	rsync -rltpDv --update ~/wip/ /usr/local/mnt/iceburg/backup/$(HOSTNAME).smeg/wip/
