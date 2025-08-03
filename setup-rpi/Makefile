IMAGE_URL = https://cdimage.ubuntu.com/releases/24.04/release/ubuntu-24.04.2-preinstalled-server-arm64+raspi.img.xz
IMAGE_FILENAME = $(notdir $(IMAGE_URL))
EXTRACTED_IMAGE = $(basename $(IMAGE_FILENAME))
SDCARD = /dev/sda

.PHONY: all download clean blank-sd write-sd first-connect setup-ssh connect-rpi

all: $(EXTRACTED_IMAGE)

$(IMAGE_FILENAME):
	curl -L $(IMAGE_URL) -o $(IMAGE_FILENAME) || wget $(IMAGE_URL) -O $(IMAGE_FILENAME)

$(EXTRACTED_IMAGE): $(IMAGE_FILENAME)
	xz -d -k -f $(IMAGE_FILENAME)

download: $(IMAGE_FILENAME)

clean:
	rm -f $(IMAGE_FILENAME) $(EXTRACTED_IMAGE)

blank-sd:
	@echo "About to erase all data on $(SDCARD). Press Ctrl+C to abort, or Enter to continue."
	@read answer
	sudo wipefs -a $(SDCARD)
	sudo dd if=/dev/zero of=$(SDCARD) bs=1M count=10
	sudo sync

write-sd: $(EXTRACTED_IMAGE)
	@echo "About to write image to $(SDCARD). Press Ctrl+C to abort, or Enter to continue."
	@read answer
	sudo dd if=$(EXTRACTED_IMAGE) of=$(SDCARD) bs=4M status=progress conv=fsync
	sudo sync
	@echo "Image written successfully. SD card is ready for Raspberry Pi."

setup-ssh:
	@echo "Setting up SSH with password auth for Raspberry Pi. Make sure SD card is mounted."
	sudo mkdir -p /mnt/rpi-boot
	sudo mount $(SDCARD)1 /mnt/rpi-boot
	@echo "Creating SSH file to enable SSH server..."
	sudo touch /mnt/rpi-boot/ssh
	@echo "Creating userconf file for password authentication..."
	sudo bash -c "echo 'ubuntu:ubuntu' > /mnt/rpi-boot/userconf"
	sudo sync
	@echo "Unmounting boot partition..."
	sudo umount /mnt/rpi-boot
	@echo "SSH setup complete. You can now boot your Raspberry Pi and connect with username 'ubuntu' and password 'ubuntu'."

