SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

RELEASE := 20260701
IMAGE := ROCKNIX-H700.aarch64-$(RELEASE)-DDR4.img.gz
CHECKSUM := $(IMAGE).sha256
BASE_URL := https://github.com/ROCKNIX/distribution/releases/download/$(RELEASE)
CACHE := .cache
IMAGE_PATH := $(CACHE)/$(IMAGE)
CHECKSUM_PATH := $(CACHE)/$(CHECKSUM)
DEVICE_TREE := sun50i-h700-anbernic-rg35xx-h.dtb
GAME_MANIFEST ?= ../kidsgames.md
BASE_GAME_MANIFEST ?= ../kidsgames.md
EXPECTED_GAMES ?= 30
NAS_ROMS := /usr/local/mnt/iceburg/backup/system.smeg/anbernic_roms
NAS_WIP_ROMS := /usr/local/mnt/iceburg/backup/system.smeg/wip/games/roms
SAVE_BACKUP_ROOT ?= /usr/local/mnt/iceburg/backup/system.smeg
SAVE_MAX_DEPTH ?= 8
EARTHBOUND_SAVE := $(SAVE_BACKUP_ROOT)/wip/games/roms/snes/EarthBound (USA).srm
CHRONO_TRIGGER_SAVE := $(SAVE_BACKUP_ROOT)/wip/games/roms/snes/Chrono Trigger - Complete (Hack v1.5).srm
PRESERVED_SAVE_DIR ?= save-backups/2026-08-23-earthbound-chrono-trigger
ROM_INVENTORY := $(CACHE)/rom-inventory.txt

.PHONY: help download verify-image inventory refresh-inventory search-games search-save-files search-backup-paths inspect-save-file compare-files preserve-saves verify-games compare-games inspect inspect-storage inspect-storage-apply inspect-save-destination inspect-save-destination-apply device-check validate prepare prepare-apply configure configure-apply copy-games copy-games-apply verify-device verify-device-apply pane-output clean

help:
	@echo "Targets:"
	@echo "  make download  Download the RG35XX H ROCKNIX image and checksum"
	@echo "  make inventory  List available SNES, Mega Drive, GBA, and FBNeo ROMs"
	@echo "  make refresh-inventory"
	@echo "  make search-games SYSTEM='path expression' PATTERN='title expression'"
	@echo "  make search-save-files SAVE_PATTERN='earthbound|chrono.*trigger'"
	@echo "  make search-backup-paths PATH_PATTERN='rocknix|games-internal'"
	@echo "  make inspect-save-file SAVE_GAME=earthbound SAVE_FILE=/path/to/game.srm"
	@echo "  make compare-files FILE_A=/path/to/one FILE_B=/path/to/two"
	@echo "  make preserve-saves  Preserve the validated EarthBound and Chrono Trigger SRAM"
	@echo "  make verify-games GAME_MANIFEST=../adultgames.md EXPECTED_GAMES=74"
	@echo "  make compare-games BASE_GAME_MANIFEST=../kidsgames.md GAME_MANIFEST=../adultgames.md"
	@echo "  make inspect DEVICE=/dev/sdX"
	@echo "  make inspect-storage DEVICE=/dev/sdX"
	@echo "  make inspect-save-destination DEVICE=/dev/sdX"
	@echo "  make prepare DEVICE=/dev/sdX CONFIRM=rocknix"
	@echo "  make configure DEVICE=/dev/sdX"
	@echo "  make copy-games DEVICE=/dev/sdX"
	@echo "  make verify-device DEVICE=/dev/sdX"
	@echo "  make pane-output PANE=%N"
	@echo "  make clean"

download: $(IMAGE_PATH) $(CHECKSUM_PATH)

inventory: $(ROM_INVENTORY)
	@cat "$(ROM_INVENTORY)"

$(ROM_INVENTORY):
	@test -d "$(NAS_ROMS)" || { echo "Missing NAS ROM backup: $(NAS_ROMS)" >&2; exit 1; }
	@test -d "$(NAS_WIP_ROMS)" || { echo "Missing NAS WIP ROM backup: $(NAS_WIP_ROMS)" >&2; exit 1; }
	@mkdir -p "$(CACHE)"
	@find "$(NAS_ROMS)" "$(NAS_WIP_ROMS)" -type f \
		\( -iname '*.sfc' -o -iname '*.smc' -o -iname '*.md' -o -iname '*.gen' -o -iname '*.gba' \
		-o -ipath '*/MD/*.bin' -o -ipath '*/megadrive/*.bin' \
		-o -ipath '*/SFC/*.zip' -o -ipath '*/snes/*.zip' -o -ipath '*/MD/*.zip' -o -ipath '*/megadrive/*.zip' -o -ipath '*/GBA/*.zip' -o -ipath '*/FBNEO/*.zip' \) \
		-print | sort > "$@.part"
	@mv "$@.part" "$@"

refresh-inventory:
	rm -f "$(ROM_INVENTORY)"
	@$(MAKE) --no-print-directory "$(ROM_INVENTORY)"

search-games:
	@test -n "$(SYSTEM)" || { echo "SYSTEM is required" >&2; exit 2; }
	@test -n "$(PATTERN)" || { echo "PATTERN is required" >&2; exit 2; }
	@$(MAKE) --no-print-directory inventory | rg -i -- "$(SYSTEM)" | rg -i -- "$(PATTERN)"

search-save-files:
	@test -d "$(SAVE_BACKUP_ROOT)" || { echo "Missing save backup root: $(SAVE_BACKUP_ROOT)" >&2; exit 1; }
	@test -n "$(SAVE_PATTERN)" || { echo "SAVE_PATTERN is required" >&2; exit 2; }
	@rg --files --hidden --no-ignore "$(SAVE_BACKUP_ROOT)" | rg -i -- "$(SAVE_PATTERN)" | \
		while IFS= read -r path; do stat --printf='%y\t%s\t%n\n' "$$path"; done | sort

search-backup-paths:
	@test -d "$(SAVE_BACKUP_ROOT)" || { echo "Missing save backup root: $(SAVE_BACKUP_ROOT)" >&2; exit 1; }
	@test -n "$(PATH_PATTERN)" || { echo "PATH_PATTERN is required" >&2; exit 2; }
	@find "$(SAVE_BACKUP_ROOT)" -mindepth 1 -maxdepth "$(SAVE_MAX_DEPTH)" -type d -printf '%f\t%p\n' | \
		rg -i -- "^($(PATH_PATTERN))\t" | sort

inspect-save-file:
	@test -f "$(SAVE_FILE)" || { echo "Missing save file: $(SAVE_FILE)" >&2; exit 1; }
	@test "$(SAVE_GAME)" = earthbound -o "$(SAVE_GAME)" = chrono-trigger || { echo "SAVE_GAME must be earthbound or chrono-trigger" >&2; exit 2; }
	@stat --printf='modified=%y size=%s path=%n\n' "$(SAVE_FILE)"
	@sha256sum "$(SAVE_FILE)"
	@case "$(SAVE_GAME)" in \
		earthbound) perl -0777 -ne 'length($$_) == 0x2000 or die "Expected 8192-byte SRAM\n"; my $$sig = "HAL Laboratory, inc."; my $$version = unpack("v",substr($$_,0x1ffe,2)); printf "version=0x%04x expected=0x0493 valid=%s\n",$$version,$$version==0x0493?"yes":"no"; my $$valid = sub { my ($$block)=@_; my $$payload=substr($$block,0x20,0x4e0); my $$sum=0; $$sum=($$sum+$$_)&0xffff for unpack("C*",$$payload); my $$xor=0; $$xor^=$$_ for unpack("v*",$$payload); my ($$ss,$$sx)=unpack("v2",substr($$block,0x1c,4)); return substr($$block,0,20) eq $$sig && $$sum==$$ss && $$xor==$$sx; }; my @pairs=([0x0000,0x0500],[0x0a00,0x0f00],[0x1300,0x1800]); for my $$i (0..2) { my ($$ao,$$bo)=@{$$pairs[$$i]}; my $$a=substr($$_,$$ao,0x500); my $$b=substr($$_,$$bo,0x500); my $$payload=substr($$a,0x20,0x4e0); my $$va=$$valid->($$a); my $$vb=$$valid->($$b); my $$nonzero=grep{$$_!=0}unpack("C*",$$payload); my @levels=map{unpack("C",substr($$payload,0x1d9+$$_*0x5f+5,1))}0..3; my $$cash=unpack("V",substr($$payload,0x3c,4)); my $$atm=unpack("V",substr($$payload,0x40,4)); printf "slot=%d populated=%s block_a_valid=%s block_b_valid=%s payload_mirror=%s levels=%s cash=%d atm=%d nonzero_bytes=%d\n",$$i+1,($$nonzero&&($$va||$$vb))?"yes":"no",$$va?"yes":"no",$$vb?"yes":"no",substr($$a,0x20,0x4e0) eq substr($$b,0x20,0x4e0)?"yes":"no",join(",",@levels),$$cash,$$atm,$$nonzero; }' "$(SAVE_FILE)" ;; \
		chrono-trigger) perl -0777 -ne 'length($$_) == 0x2000 or die "Expected 8192-byte SRAM\n"; printf "last_save_raw=%d\n",unpack("C",substr($$_,0x1fe0,1)); for my $$i (0..2) { my $$slot=substr($$_,$$i*0x0a00,0x0a00); my $$stored=unpack("v",substr($$_,0x1ff0+$$i*2,2)); my $$sum=0; my @words=unpack("v*",$$slot); for my $$word (reverse @words) { $$sum-=0xffff if $$sum>0xffff; $$sum+=$$word; } $$sum&=0xffff; my $$save_count=unpack("C",substr($$slot,0x59c,1)); my @gb=unpack("C3",substr($$slot,0x5e0,3)); my $$gold=$$gb[0]+($$gb[1]<<8)+($$gb[2]<<16); my @levels=map{unpack("C",substr($$slot,0x200+$$_*0x50+0x12,1))}0..6; my $$milliseconds=unpack("v",substr($$slot,0x5e3,2)); my $$seconds=unpack("C",substr($$slot,0x5e5,1)); my $$minutes=unpack("C",substr($$slot,0x5e6,1)); my $$hours=unpack("v",substr($$slot,0x5e7,2)); my $$nonzero=grep{$$_!=0}unpack("C*",$$slot); printf "slot=%d populated=%s checksum=%s stored=0x%04x calculated=0x%04x saves=%d gold=%d levels=%s time=%d:%02d:%02d.%d nonzero_bytes=%d\n",$$i+1,($$nonzero&&$$stored==$$sum)?"yes":"no",$$stored==$$sum?"yes":"no",$$stored,$$sum,$$save_count,$$gold,join(",",@levels),$$hours,$$minutes,$$seconds,$$milliseconds,$$nonzero; }' "$(SAVE_FILE)" ;; \
	 esac

compare-files:
	@test -f "$(FILE_A)" || { echo "Missing file: $(FILE_A)" >&2; exit 1; }
	@test -f "$(FILE_B)" || { echo "Missing file: $(FILE_B)" >&2; exit 1; }
	@sha256sum "$(FILE_A)" "$(FILE_B)"
	@cmp --silent "$(FILE_A)" "$(FILE_B)" || { echo "Files differ" >&2; exit 1; }
	@echo "Files are byte-for-byte identical."

preserve-saves:
	@test -f "$(EARTHBOUND_SAVE)" || { echo "Missing EarthBound save: $(EARTHBOUND_SAVE)" >&2; exit 1; }
	@test -f "$(CHRONO_TRIGGER_SAVE)" || { echo "Missing Chrono Trigger save: $(CHRONO_TRIGGER_SAVE)" >&2; exit 1; }
	@test "$$(stat --printf='%s' "$(EARTHBOUND_SAVE)")" -eq 8192 || { echo "EarthBound save is not 8192 bytes" >&2; exit 1; }
	@test "$$(stat --printf='%s' "$(CHRONO_TRIGGER_SAVE)")" -eq 8192 || { echo "Chrono Trigger save is not 8192 bytes" >&2; exit 1; }
	@test ! -e "$(PRESERVED_SAVE_DIR)" || { echo "Refusing to overwrite existing archive: $(PRESERVED_SAVE_DIR)" >&2; exit 1; }
	@mkdir -p "$(PRESERVED_SAVE_DIR)"
	@cp --preserve=timestamps "$(EARTHBOUND_SAVE)" "$(PRESERVED_SAVE_DIR)/EarthBound (USA).srm"
	@cp --preserve=timestamps "$(CHRONO_TRIGGER_SAVE)" "$(PRESERVED_SAVE_DIR)/Chrono Trigger - Complete (Hack v1.5).srm"
	@chmod 0444 "$(PRESERVED_SAVE_DIR)/EarthBound (USA).srm" "$(PRESERVED_SAVE_DIR)/Chrono Trigger - Complete (Hack v1.5).srm"
	@cd "$(PRESERVED_SAVE_DIR)" && sha256sum "EarthBound (USA).srm" "Chrono Trigger - Complete (Hack v1.5).srm" > SHA256SUMS
	@chmod 0444 "$(PRESERVED_SAVE_DIR)/SHA256SUMS"
	@cd "$(PRESERVED_SAVE_DIR)" && sha256sum --check --strict SHA256SUMS
	@echo "Preserved validated saves in $(PRESERVED_SAVE_DIR)."

verify-games:
	@test -f "$(GAME_MANIFEST)" || { echo "Missing game manifest: $(GAME_MANIFEST)" >&2; exit 1; }
	@count=0; while IFS= read -r source; do \
		test -f "$$source" || { echo "Missing source ROM: $$source" >&2; exit 1; }; \
		count=$$((count + 1)); \
	done < <(awk '/^  `/{sub(/^  `/, ""); sub(/`$$/, ""); print}' "$(GAME_MANIFEST)"); \
		test "$$count" -eq "$(EXPECTED_GAMES)" || { echo "Expected $(EXPECTED_GAMES) games in $(GAME_MANIFEST), found $$count" >&2; exit 1; }; \
		echo "Verified $$count ROM paths in $(GAME_MANIFEST)."

compare-games:
	@test -f "$(BASE_GAME_MANIFEST)" || { echo "Missing base game manifest: $(BASE_GAME_MANIFEST)" >&2; exit 1; }
	@test -f "$(GAME_MANIFEST)" || { echo "Missing game manifest: $(GAME_MANIFEST)" >&2; exit 1; }
	@missing="$$(comm -23 \
		<(awk '/^  `/{sub(/^  `/, ""); sub(/`$$/, ""); print}' "$(BASE_GAME_MANIFEST)" | sort -u) \
		<(awk '/^  `/{sub(/^  `/, ""); sub(/`$$/, ""); print}' "$(GAME_MANIFEST)" | sort -u))"; \
	if test -n "$$missing"; then \
		echo "Paths in $(BASE_GAME_MANIFEST) missing from $(GAME_MANIFEST):"; \
		printf '%s\n' "$$missing"; \
		exit 1; \
	fi; \
	echo "$(GAME_MANIFEST) contains every ROM path from $(BASE_GAME_MANIFEST)."

$(IMAGE_PATH):
	mkdir -p $(CACHE)
	curl --fail --location --output $@.part $(BASE_URL)/$(IMAGE)
	mv $@.part $@

$(CHECKSUM_PATH):
	mkdir -p $(CACHE)
	curl --fail --location --output $@.part $(BASE_URL)/$(CHECKSUM)
	mv $@.part $@

verify-image: download
	cd $(CACHE) && sha256sum --check --strict $(CHECKSUM)
	gzip --list "$(IMAGE_PATH)"

inspect:
	@test -n "$(DEVICE)" || { echo "DEVICE is required" >&2; exit 2; }
	@lsblk -o NAME,PATH,RM,SIZE,TYPE,FSTYPE,LABEL,MOUNTPOINTS,MODEL,VENDOR,TRAN "$(DEVICE)"

inspect-storage:
	bash ../../pane.sh inspect-rg35xx-storage $(MAKE) inspect-storage-apply DEVICE="$(DEVICE)"

inspect-storage-apply: device-check
	@mount_dir="$$(mktemp -d)"; mounted=0; \
		cleanup() { if [ "$$mounted" -eq 1 ]; then sudo umount "$$mount_dir"; fi; rmdir "$$mount_dir"; }; \
		trap cleanup EXIT; \
		test -b "$(DEVICE)2" || { echo "Missing ROCKNIX storage partition: $(DEVICE)2" >&2; exit 1; }; \
		sudo mount -o ro "$(DEVICE)2" "$$mount_dir"; mounted=1; \
		sudo find "$$mount_dir" -maxdepth 3 -type d -printf '%P\n' | sort; \
		sudo umount "$$mount_dir"; mounted=0; \
		rmdir "$$mount_dir"; trap - EXIT

inspect-save-destination:
	bash ../../pane.sh inspect-rg35xx-saves $(MAKE) inspect-save-destination-apply DEVICE="$(DEVICE)"

inspect-save-destination-apply: device-check
	@mount_dir="$$(mktemp -d)"; mounted=0; \
		cleanup() { if [ "$$mounted" -eq 1 ]; then sudo umount "$$mount_dir"; fi; rmdir "$$mount_dir"; }; \
		trap cleanup EXIT; \
		test -b "$(DEVICE)2" || { echo "Missing ROCKNIX storage partition: $(DEVICE)2" >&2; exit 1; }; \
		sudo mount -o ro "$(DEVICE)2" "$$mount_dir"; mounted=1; \
		echo "Save directories:"; \
		sudo find "$$mount_dir" -maxdepth 8 -type d \( -iname saves -o -iname savestates -o -iname states \) -printf '%P\n' | sort; \
		mapfile -t configs < <(sudo find "$$mount_dir" -maxdepth 8 -type f -name retroarch.cfg -print); \
		test "$${#configs[@]}" -gt 0 || { echo "No RetroArch configuration found on $(DEVICE)2" >&2; exit 1; }; \
		for config in "$${configs[@]}"; do \
			echo "RetroArch config: $${config#$$mount_dir/}"; \
			sudo awk '/^(savefile_directory|savestate_directory|sort_savefiles|sort_savestates)/ { print }' "$$config"; \
		done; \
		sudo umount "$$mount_dir"; mounted=0; \
		rmdir "$$mount_dir"; trap - EXIT

device-check:
	@test -n "$(DEVICE)" || { echo "DEVICE is required" >&2; exit 2; }
	@test -b "$(DEVICE)" || { echo "Not a block device: $(DEVICE)" >&2; exit 2; }
	@test "$$(lsblk -dnro TYPE "$(DEVICE)")" = disk || { echo "DEVICE must be a whole disk: $(DEVICE)" >&2; exit 2; }
	@test "$$(lsblk -dnro RM "$(DEVICE)")" = 1 || { echo "DEVICE is not reported as removable: $(DEVICE)" >&2; exit 2; }

validate: device-check
	@test "$(CONFIRM)" = rocknix || { echo "Set CONFIRM=rocknix to authorize erasing $(DEVICE)" >&2; exit 2; }

prepare:
	bash ../../pane.sh prep-rg35xx $(MAKE) prepare-apply DEVICE="$(DEVICE)" CONFIRM="$(CONFIRM)"

prepare-apply: validate verify-image
	@lsblk -o NAME,PATH,RM,SIZE,TYPE,FSTYPE,LABEL,MOUNTPOINTS,MODEL,VENDOR,TRAN "$(DEVICE)"
	@lsblk -lnpo PATH "$(DEVICE)" | tac | while read -r block; do \
		if findmnt -rn -S "$$block" >/dev/null; then sudo umount "$$block"; fi; \
	done
	gzip --decompress --stdout "$(IMAGE_PATH)" | sudo dd of="$(DEVICE)" bs=4M iflag=fullblock status=progress conv=fsync
	sync
	@echo "ROCKNIX $(RELEASE) written to $(DEVICE)."

configure:
	bash ../../pane.sh configure-rg35xx $(MAKE) configure-apply DEVICE="$(DEVICE)"

configure-apply: device-check
	@mount_dir="$$(mktemp -d)"; mounted=0; \
		cleanup() { if [ "$$mounted" -eq 1 ]; then sudo umount "$$mount_dir"; fi; rmdir "$$mount_dir"; }; \
		trap cleanup EXIT; \
		test -b "$(DEVICE)1" || { echo "Missing ROCKNIX boot partition: $(DEVICE)1" >&2; exit 1; }; \
		echo "Mounting $(DEVICE)1..."; \
		sudo mount -o rw "$(DEVICE)1" "$$mount_dir"; mounted=1; \
		test -f "$$mount_dir/device_trees/$(DEVICE_TREE)" || { echo "Missing RG35XX H device tree: $(DEVICE_TREE)" >&2; exit 1; }; \
		echo "Installing $(DEVICE_TREE) as dtb.img..."; \
		sudo install -m 0644 "$$mount_dir/device_trees/$(DEVICE_TREE)" "$$mount_dir/dtb.img"; \
		sudo cmp --silent "$$mount_dir/device_trees/$(DEVICE_TREE)" "$$mount_dir/dtb.img"; \
		sync; \
		sudo umount "$$mount_dir"; mounted=0; \
		rmdir "$$mount_dir"; trap - EXIT; \
		sudo blockdev --flushbufs "$(DEVICE)"; \
		echo "RG35XX H device tree installed; $(DEVICE) is ready to remove."

copy-games:
	bash ../../pane.sh copy-rg35xx-games $(MAKE) copy-games-apply DEVICE="$(DEVICE)" GAME_MANIFEST="$(GAME_MANIFEST)" EXPECTED_GAMES="$(EXPECTED_GAMES)"

copy-games-apply: device-check
	@test -f "$(GAME_MANIFEST)" || { echo "Missing game manifest: $(GAME_MANIFEST)" >&2; exit 1; }
	@mount_dir="$$(mktemp -d)"; mounted=0; count=0; \
		cleanup() { if [ "$$mounted" -eq 1 ]; then sudo umount "$$mount_dir"; fi; rmdir "$$mount_dir"; }; \
		trap cleanup EXIT; \
		test -b "$(DEVICE)2" || { echo "Missing ROCKNIX storage partition: $(DEVICE)2" >&2; exit 1; }; \
		echo "Mounting $(DEVICE)2..."; \
		sudo mount -o rw "$(DEVICE)2" "$$mount_dir"; mounted=1; \
		for system in snes megadrive gba fbneo; do \
			test -d "$$mount_dir/games-internal/roms/$$system" || { echo "Missing ROCKNIX ROM directory: games-internal/roms/$$system" >&2; exit 1; }; \
		done; \
		while IFS= read -r source; do \
			test -f "$$source" || { echo "Missing source ROM: $$source" >&2; exit 1; }; \
			case "$$source" in \
				*.sfc|*.smc) system=snes ;; \
				*.md) system=megadrive ;; \
				*.gba) system=gba ;; \
				*/FBNEO/*.zip) system=fbneo ;; \
				*) echo "Unsupported ROM in manifest: $$source" >&2; exit 1 ;; \
			esac; \
			filename="$${source##*/}"; \
			echo "Copying $$system/$$filename"; \
			sudo install -m 0644 "$$source" "$$mount_dir/games-internal/roms/$$system/$$filename"; \
			sudo cmp --silent "$$source" "$$mount_dir/games-internal/roms/$$system/$$filename"; \
			count=$$((count + 1)); \
		done < <(awk '/^  `/{sub(/^  `/, ""); sub(/`$$/, ""); print}' "$(GAME_MANIFEST)"); \
		test "$$count" -eq "$(EXPECTED_GAMES)" || { echo "Expected $(EXPECTED_GAMES) games in $(GAME_MANIFEST), found $$count" >&2; exit 1; }; \
		sync; \
		sudo umount "$$mount_dir"; mounted=0; \
		rmdir "$$mount_dir"; trap - EXIT; \
		sudo blockdev --flushbufs "$(DEVICE)"; \
		echo "Copied and verified $$count curated games; $(DEVICE) is ready to remove."

verify-device:
	bash ../../pane.sh verify-rg35xx $(MAKE) verify-device-apply DEVICE="$(DEVICE)"

verify-device-apply: device-check verify-image
	@size="$$(gzip --list "$(IMAGE_PATH)" | awk 'END { print $$2 }')"; \
		image_hash="$$(gzip --decompress --stdout "$(IMAGE_PATH)" | sha256sum | cut -d' ' -f1)"; \
		device_hash="$$(sudo head --bytes="$$size" "$(DEVICE)" | sha256sum | cut -d' ' -f1)"; \
		test "$$device_hash" = "$$image_hash" || { echo "Device content does not match the ROCKNIX image" >&2; exit 1; }; \
		echo "Device content matches all $$size bytes of the ROCKNIX image."
	sudo blockdev --rereadpt "$(DEVICE)"
	sudo udevadm settle
	@lsblk -o NAME,PATH,RM,SIZE,TYPE,FSTYPE,LABEL,MOUNTPOINTS,MODEL,VENDOR,TRAN "$(DEVICE)"

pane-output:
	@test -n "$(PANE)" || { echo "PANE is required" >&2; exit 2; }
	tmux capture-pane -p -S - -t "$(PANE)"

clean:
	rm -rf $(CACHE)
