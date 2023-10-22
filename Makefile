

run:
	ansible-playbook main.yml -c local -K
	swaymsg reload
	git add -A 
	git commit -am "update" && git push
