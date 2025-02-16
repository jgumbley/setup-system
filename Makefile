.PHONY: run push check-thumb

run:
	ansible-playbook main.yml -c local -K
	swaymsg reload

push:
	git add -A 
	git commit -am "update" && git push
