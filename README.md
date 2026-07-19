# System Setup

This repository contains Ansible playbooks and configurations to automate the setup of my development environments on both macOS and Linux.

## Quick Start

The setup process is primarily driven by `make` commands which wrap Ansible playbooks.

1.  **Bootstrap:** Run the appropriate bootstrap script for your OS. This installs essential dependencies like Ansible.
    *   **Ubuntu:** `./bootstrap/ubuntu.sh`
    *   **macOS:** `./bootstrap/darwin.sh`

2.  **Updates:** Quickly refresh coding agents.
    ```bash
    make updates
    ```

3.  **Terminal:** Configure the terminal environment (fish, tmux, vim, git, kitty).
    ```bash
    make term
    ```

4.  **Full Setup:** Fully converge the local machine based on its hostname.
    ```bash
    make setup
    ```
    This applies shared tools, 1Password CLI, and machine-specific roles.

## Makefile Commands

*   `make updates`: Refreshes coding agents through `updates.yml`. This requires privilege escalation and may prompt for a password.
*   `make nas`: Runs the `nas.yml` playbook to mount the NAS (macOS uses the current user with sudo privileges).
*   `make term`: Runs the `terminal.yml` playbook to configure the terminal environment.
*   `make setup`: Runs `setup.yml` to fully converge the local machine using its exact hostname, including HAL's complete Sunshine/Sway host service.
*   `make -C utils/hal_low_power apply`: Temporarily minimizes HAL's CPU and GPU power use until its next reboot without changing Wi-Fi.
*   `make backup`: Ensures the NAS is mounted, backs up `~/wip`, and on HAL separately protects Sunshine's pairing state and certificate/key under the host backup's `sunshine/` directory.

## Ansible Structure

The configuration is managed by Ansible playbooks and roles.

### Playbooks

*   `updates.yml`: Refreshes coding agents.
*   `terminal.yml`: Configures the terminal environment using the `terminal` role.
*   `setup.yml`: Applies shared foundational tools through `core-tools`, installs the 1Password CLI, then applies roles selected by the machine's exact hostname. The hostname-to-role mapping is defined in `machines.yml`.

### Roles

*   `core-tools`: Installs common command-line tools and system-wide shell environment support.
*   `nas-mount`: Mounts the network-attached storage.
*   `sway-desktop`: Sets up the Sway tiling window manager and related tools for a graphical Linux environment.
*   `sunshine-host`: Fully configures HAL's native Sunshine package, input and seat permissions, headless Sway session, launchers, application list, persistent state directory, and boot-time systemd services. External OpenMW and games content remains under the fully qualified `/home/system/wip/mw` and `/home/system/wip/games` locations.
*   `godot`: Installs the Godot Engine editor binary from https://godotengine.org/download (no extra runtime dependencies; bring your own editor/IDE).
*   `terminal`: Configures fish, tmux, vim, git, and other terminal applications.

### Configuration

*   `machines.yml`: Defines which roles to apply to each exact hostname.
*   `group_vars/all/theme.yml`: Contains a centralized color scheme used across various applications like kitty and Waybar.

## Sunshine Host Operations on HAL

The Sunshine role is applied only through `make setup`. Runtime operations and
the committed Moonlight cover-art source are self-contained under
`utils/sunshine_host`:

```bash
make -C utils/sunshine_host status
make -C utils/sunshine_host verify
make -C utils/sunshine_host pairings
make -C utils/sunshine_host pin PIN=1234 PASSWORD='...'
```

Live pairing state remains private under `/var/lib/sunshine-host`; setup creates
that directory but never imports or overwrites its credential files.

## Quest Client Operations on HAL

Quest USB, ADB, and Moonlight APK operations are isolated from the Sunshine
host utility:

```bash
make -C utils/quest_client check
make -C utils/quest_client install-pane
make -C utils/quest_client wireless-pair IP_PORT=192.168.1.x:pair-port
make -C utils/quest_client install-wireless IP_PORT=192.168.1.x:adb-port
make -C utils/quest_client mtp-enable
```

The Quest utility consumes the APK root from the Ansible-managed
`/etc/setup-system/hal-locations.mk` file rather than defining another
workspace path.
