SHELL := /bin/bash
.DEFAULT_GOAL := help

RELEASE := 26.04
IMAGE := ubuntu-$(RELEASE)-preinstalled-server-arm64+raspi.img.xz
BASE_URL := https://cdimage.ubuntu.com/ubuntu/releases/$(RELEASE)/release
CACHE := .cache
IMAGE_PATH := $(CACHE)/$(IMAGE)
CHECKSUMS := $(CACHE)/SHA256SUMS
REPO_ROOT := ../..
SSH_HOST := system@legobrick
REMOTE_REPO := /home/system/wip/setup-system
REPOSITORY := https://github.com/jgumbley/setup-system.git

.PHONY: help download verify-image inspect validate prepare prepare-apply preflight commission commission-apply setup setup-apply verify verify-apply clean

help:
	@echo "Targets:"
	@echo "  make inspect DEVICE=/dev/sdX"
	@echo "  make prepare DEVICE=/dev/sdX CONFIRM=legobrick"
	@echo "  make preflight"
	@echo "  make commission"
	@echo "  make setup"
	@echo "  make verify"
	@echo "  make clean"

download: $(IMAGE_PATH) $(CHECKSUMS)

$(IMAGE_PATH):
	mkdir -p $(CACHE)
	curl --fail --location --output $@.part $(BASE_URL)/$(IMAGE)
	mv $@.part $@

$(CHECKSUMS):
	mkdir -p $(CACHE)
	curl --fail --location --output $@.part $(BASE_URL)/SHA256SUMS
	mv $@.part $@

verify-image: download
	cd $(CACHE) && grep " \\*$(IMAGE)$$" SHA256SUMS | sha256sum --check --strict

inspect:
	@test -n "$(DEVICE)" || { echo "DEVICE is required" >&2; exit 2; }
	@lsblk -o NAME,PATH,RM,SIZE,TYPE,FSTYPE,LABEL,MOUNTPOINTS,MODEL,TRAN $(DEVICE)

validate:
	@test -n "$(DEVICE)" || { echo "DEVICE is required" >&2; exit 2; }
	@test "$(CONFIRM)" = legobrick || { echo "Set CONFIRM=legobrick to authorize erasing $(DEVICE)" >&2; exit 2; }

prepare:
	bash ../../pane.sh prep-legobrick-sd $(MAKE) prepare-apply DEVICE=$(DEVICE) CONFIRM=$(CONFIRM)

prepare-apply: validate verify-image
	./prepare.sh $(DEVICE) $(IMAGE_PATH) $(REPO_ROOT)/roles/ssh_host/files/ssh_keys

preflight:
	ssh $(SSH_HOST) "make --no-print-directory --eval 'preflight: ; hostname | grep -qx legobrick && dpkg --print-architecture | grep -qx arm64 && grep -qx \"VERSION_ID=\\\"26.04\\\"\" /etc/os-release && cloud-init status | grep -qx \"status: done\" && command -v git && command -v make' preflight"

commission:
	bash ../../pane.sh commission-legobrick $(MAKE) commission-apply

commission-apply: preflight
	ssh -tt $(SSH_HOST) "make --no-print-directory --eval 'commission: ; mkdir -p /home/system/wip; git clone $(REPOSITORY) $(REMOTE_REPO); make -C $(REMOTE_REPO) setup' commission"

setup:
	bash ../../pane.sh setup-legobrick $(MAKE) setup-apply

setup-apply:
	ssh -tt $(SSH_HOST) "make -C $(REMOTE_REPO) setup"

verify:
	bash ../../pane.sh verify-legobrick $(MAKE) verify-apply

verify-apply:
	ssh $(SSH_HOST) "make --no-print-directory --eval 'verify: ; hostname | grep -qx legobrick && id -un | grep -qx system && sudo sshd -T | grep -qx \"passwordauthentication no\" && test -s /home/system/.ssh/authorized_keys && getent passwd system | cut -d: -f7 | grep -qx /usr/bin/fish' verify"

clean:
	rm -rf $(CACHE)
