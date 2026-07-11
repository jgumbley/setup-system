SHELL := /bin/bash
.DEFAULT_GOAL := help

RELEASE := 26.04
IMAGE := ubuntu-$(RELEASE)-preinstalled-server-arm64+raspi.img.xz
BASE_URL := https://cdimage.ubuntu.com/ubuntu/releases/$(RELEASE)/release
CACHE := .cache
IMAGE_PATH := $(CACHE)/$(IMAGE)
CHECKSUMS := $(CACHE)/SHA256SUMS
REPO_ROOT := ../..

.PHONY: help download verify-image inspect validate prepare clean

help:
	@echo "Targets:"
	@echo "  make inspect DEVICE=/dev/sdX"
	@echo "  make prepare DEVICE=/dev/sdX CONFIRM=legobrick"
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
	cd $(CACHE) && grep "  $(IMAGE)$$" SHA256SUMS | sha256sum --check --strict

inspect:
	@test -n "$(DEVICE)" || { echo "DEVICE is required" >&2; exit 2; }
	@lsblk -o NAME,PATH,RM,SIZE,TYPE,FSTYPE,LABEL,MOUNTPOINTS,MODEL,TRAN $(DEVICE)

validate:
	@test -n "$(DEVICE)" || { echo "DEVICE is required" >&2; exit 2; }
	@test "$(CONFIRM)" = legobrick || { echo "Set CONFIRM=legobrick to authorize erasing $(DEVICE)" >&2; exit 2; }

prepare: validate verify-image
	./prepare.sh $(DEVICE) $(IMAGE_PATH) $(REPO_ROOT)/roles/ssh_host/files/ssh_keys

clean:
	rm -rf $(CACHE)
