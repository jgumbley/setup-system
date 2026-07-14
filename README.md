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

5.  **Sunshine Host on HAL:** Install or verify only HAL's native Sunshine host package and input permissions.
    ```bash
    make sunshine-host
    ```

## Makefile Commands

*   `make updates`: Refreshes coding agents through `updates.yml`. This requires privilege escalation and may prompt for a password.
*   `make nas`: Runs the `nas.yml` playbook to mount the NAS (macOS uses the current user with sudo privileges).
*   `make term`: Runs the `terminal.yml` playbook to configure the terminal environment.
*   `make setup`: Runs `setup.yml` to fully converge the local machine using its exact hostname, without refreshing coding agents.
*   `make sunshine-host`: Applies only HAL's native Sunshine package and host input/seat permissions through a supervised pane.
*   `make backup`: Ensures the NAS is mounted, then backs up the `~/wip` directory to the NAS.

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
*   `sunshine-host`: Installs the native Sunshine package and HAL's host input/seat permissions.
*   `godot`: Installs the Godot Engine editor binary from https://godotengine.org/download (no extra runtime dependencies; bring your own editor/IDE).
*   `terminal`: Configures fish, tmux, vim, git, and other terminal applications.

### Configuration

*   `machines.yml`: Defines which roles to apply to each exact hostname.
*   `group_vars/all/theme.yml`: Contains a centralized color scheme used across various applications like kitty and Waybar.
