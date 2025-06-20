.PHONY: cross-platform linux mac config push term core-tools

.bootstrapped:
ifeq ($(shell uname -s),Darwin)
	su admin -c "cd $(PWD) && ./bootstrap/darwin.sh" && touch .bootstrapped
else
	./bootstrap.sh && touch .bootstrapped
endif

cross-platform:
	ansible-playbook cross-platform.yml -c local

linux: cross-platform
	ansible-playbook linux.yml -c local -K
	swaymsg reload

mac: 
	./setup-mac/bootstrap.sh

config:
	ansible-playbook config.yml -c local -K
	swaymsg reload

core-tools: .bootstrapped
ifeq ($(shell uname -s),Darwin)
	su admin -c "cd $(PWD) && ANSIBLE_REMOTE_TMP=/tmp ansible-playbook core-tools.yml -c local"
else
	ansible-playbook core-tools.yml -c local
endif

term:
	ansible-playbook terminal.yml

push:
	git add -A 
	git commit -am "update" && git push
