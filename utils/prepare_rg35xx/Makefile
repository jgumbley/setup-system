SHELL := /bin/bash
.DEFAULT_GOAL := help

RELEASE := 20260701
IMAGE := ROCKNIX-H700.aarch64-$(RELEASE)-DDR4.img.gz
CHECKSUM := $(IMAGE).sha256
BASE_URL := https://github.com/ROCKNIX/distribution/releases/download/$(RELEASE)
CACHE := .cache
IMAGE_PATH := $(CACHE)/$(IMAGE)
CHECKSUM_PATH := $(CACHE)/$(CHECKSUM)

.PHONY: help download clean

help:
	@echo "Targets:"
	@echo "  make download  Download the RG35XX H ROCKNIX image and checksum"
	@echo "  make clean"

download: $(IMAGE_PATH) $(CHECKSUM_PATH)

$(IMAGE_PATH):
	mkdir -p $(CACHE)
	curl --fail --location --output $@.part $(BASE_URL)/$(IMAGE)
	mv $@.part $@

$(CHECKSUM_PATH):
	mkdir -p $(CACHE)
	curl --fail --location --output $@.part $(BASE_URL)/$(CHECKSUM)
	mv $@.part $@

clean:
	rm -rf $(CACHE)
