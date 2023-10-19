

run:
	ansible-playbook basics.yml -c local
	ansible-playbook sway.yml -c local
	git commit -am "update" && git push
