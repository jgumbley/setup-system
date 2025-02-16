.PHONY: run push install roo thumb unmount ps2

~/Makefile:
	ln -sf $(PWD)/Makefile ~/Makefile


wip/gen-ai/Roo-Code/bin/roo-cline-3.3.20.vsix:
	cd wip/gen-ai/Roo-Code && \
	npm run install:all && \
	npm run build

roo:
	code --install-extension ~/wip/gen-ai/Roo-Code/bin/roo-cline-3.3.20.vsix

thumb: /mnt/thumb/present.txt

/mnt/thumb/present.txt:
	sudo mkdir -p /mnt/thumb
	sudo mount /dev/sdb1 /mnt/thumb

unmount:
	sudo umount /mnt/thumb

ps2: thumb
	sudo mkdir -p /mnt/thumb/psrom
	sudo find /home/system/wip/games/roms/ps2 -name "*.7z" -exec 7z x {} -o/mnt/thumb/psrom \;
