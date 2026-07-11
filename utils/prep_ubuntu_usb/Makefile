SHELL := /bin/bash
.DEFAULT_GOAL := help

RELEASE := 26.04
IMAGE := ubuntu-$(RELEASE)-desktop-amd64.iso
BASE_URL := https://releases.ubuntu.com/$(RELEASE)
CACHE := .cache
IMAGE_PATH := $(CACHE)/$(IMAGE)
CHECKSUMS := $(CACHE)/SHA256SUMS

.PHONY: help download verify-image inspect validate prepare clean

help:
	@echo "Targets:"
	@echo "  make inspect DEVICE=/dev/sdX"
	@echo "  make prepare DEVICE=/dev/sdX CONFIRM=rocks"
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
	@lsblk -o NAME,PATH,RM,SIZE,TYPE,FSTYPE,LABEL,MOUNTPOINTS,MODEL,VENDOR,TRAN $(DEVICE)

validate:
	@test -n "$(DEVICE)" || { echo "DEVICE is required" >&2; exit 2; }
	@test "$(CONFIRM)" = rocks || { echo "Set CONFIRM=rocks to authorize erasing $(DEVICE)" >&2; exit 2; }

prepare: validate verify-image
	./prepare.sh $(DEVICE) $(IMAGE_PATH)

clean:
	rm -rf $(CACHE)
