#!/bin/bash

sudo apt install ansible git -y
ansible-playbook playbook.yml -c local
