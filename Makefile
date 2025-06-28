.PHONY: cross-platform linux mac config push term core-tools backup

.bootstrapped:
ifeq ($(shell uname -s),Darwin)
	su admin -c "cd $(PWD) && ./bootstrap/darwin.sh" && touch .bootstrapped
else
	./bootstrap.sh && touch .bootstrapped
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
	mkdir -p /usr/local/mnt/iceburg/backup/$$(hostname).smeg/wip
	rsync -av --update ~/wip/ /usr/local/mnt/iceburg/backup/$$(hostname).smeg/wip/
