.PHONY: cross-platform linux mac config push term core-tools

cross-platform:
	ansible-playbook cross-platform.yml -c local

linux: cross-platform
	ansible-playbook linux.yml -c local -K
	swaymsg reload

mac: cross-platform
	ansible-playbook mac.yml -c local -K
	./setup-mac/bootstrap.sh

config:
	ansible-playbook config.yml -c local -K
	swaymsg reload

core-tools:
	ansible-playbook core-tools.yml -c local -K

term:
	ansible-playbook terminal.yml

push:
	git add -A 
	git commit -am "update" && git push
