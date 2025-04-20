.PHONY: run push config linux mac mac-brew

run:
	ansible-playbook shared.yml -c local -K

linux: run
	ansible-playbook linux.yml -c local -K
	swaymsg reload

config:
	ansible-playbook config.yml -c local -K
	swaymsg reload

push:
	git add -A 
	git commit -am "update" && git push

mac:
	su admin -c "make mac-brew"

mac-brew:
	./setup-mac/bootstrap.sh
