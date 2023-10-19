

run:
	ansible-playbook basics.yml -c local -K
	ansible-playbook sway.yml -c local -K
	swaymsg reload
	git commit -am "update" && git push
