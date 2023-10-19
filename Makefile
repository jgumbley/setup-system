

run:
	ansible-playbook playbook.yml -c local
	git commit -am "update" && git push
