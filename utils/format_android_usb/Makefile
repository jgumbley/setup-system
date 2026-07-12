SHELL := /bin/bash
.DEFAULT_GOAL := help

.PHONY: help inspect validate format format-apply

help:
	@echo "Targets:"
	@echo "  make inspect DEVICE=/dev/sdX"
	@echo "  make format DEVICE=/dev/sdX CONFIRM=LEXAR"

inspect:
	@test -n "$(DEVICE)" || { echo "DEVICE is required" >&2; exit 2; }
	@lsblk -d -o NAME,PATH,RM,SIZE,TYPE,FSTYPE,LABEL,MOUNTPOINTS,MODEL,VENDOR,TRAN "$(DEVICE)"
	@lsblk -o NAME,PATH,RM,SIZE,TYPE,FSTYPE,LABEL,MOUNTPOINTS "$(DEVICE)"

validate:
	@test -n "$(DEVICE)" || { echo "DEVICE is required" >&2; exit 2; }
	@test "$(CONFIRM)" = LEXAR || { echo "Set CONFIRM=LEXAR to authorize erasing $(DEVICE)" >&2; exit 2; }
	@test "$$(lsblk -dnro TYPE "$(DEVICE)")" = disk || { echo "$(DEVICE) is not a whole disk" >&2; exit 1; }
	@test "$$(lsblk -dnro RM "$(DEVICE)")" = 1 || { echo "$(DEVICE) is not removable" >&2; exit 1; }
	@test "$$(lsblk -dnro TRAN "$(DEVICE)")" = usb || { echo "$(DEVICE) is not connected over USB" >&2; exit 1; }
	@lsblk -dnro VENDOR,MODEL "$(DEVICE)" | grep -Eiq 'lexar' || { echo "$(DEVICE) is not identified as Lexar" >&2; exit 1; }
	@size="$$(lsblk -bdnro SIZE "$(DEVICE)")"; test "$$size" -ge 60000000000 -a "$$size" -le 70000000000 || { echo "$(DEVICE) is not a 64 GB-class device" >&2; exit 1; }
	@test -z "$$(lsblk -nrpo MOUNTPOINTS "$(DEVICE)" | grep -v '^$$')" || { echo "$(DEVICE) or one of its partitions is mounted" >&2; exit 1; }
	@command -v parted >/dev/null || { echo "parted is unavailable" >&2; exit 1; }
	@command -v mkfs.exfat >/dev/null || { echo "mkfs.exfat is unavailable; install exfatprogs" >&2; exit 1; }

format:
	bash ../../pane.sh format-android-usb $(MAKE) format-apply DEVICE=$(DEVICE) CONFIRM=$(CONFIRM)

format-apply: validate
	sudo wipefs --all "$(DEVICE)"
	sudo parted --script "$(DEVICE)" mklabel gpt mkpart primary 1MiB 100%
	sudo partprobe "$(DEVICE)"
	sudo udevadm settle
	sudo mkfs.exfat -n ANDROID "$$(lsblk -nrpo PATH,TYPE "$(DEVICE)" | awk '$$2 == "part" { print $$1 }')"
	sudo udevadm trigger --action=change "$$(lsblk -nrpo PATH,TYPE "$(DEVICE)" | awk '$$2 == "part" { print $$1 }')"
	sudo udevadm settle
	@lsblk -o NAME,PATH,RM,SIZE,TYPE,FSTYPE,LABEL,MOUNTPOINTS "$(DEVICE)"
