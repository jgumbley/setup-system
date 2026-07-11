#!/usr/bin/env bash
set -euo pipefail

# This bootstrap targets Ubuntu 26.04 only and must never be made backwards compatible.
sudo apt-get update
sudo apt-get install --yes ansible-core git
sudo update-alternatives --set sudo /usr/bin/sudo.ws
ansible-galaxy collection install community.general
