.PHONY: run push check-thumb config

run: config
	ansible-playbook main.yml -c local -K
	swaymsg reload

config:
	ansible-playbook config.yml -c local -K
	swaymsg reload

push:
	git add -A 
	git commit -am "update" && git push
