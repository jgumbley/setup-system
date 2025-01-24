.PHONY: run push

run:
	ansible-playbook main.yml -c local -K
	swaymsg reload

push:
	git add -A 
	git commit -am "update" && git push
