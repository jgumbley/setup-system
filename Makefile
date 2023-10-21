

run:
	ansible-playbook main.yml -c local -K
	swaymsg reload
	git commit -am "update" && git push
