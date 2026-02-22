# System Setup

This repository contains Ansible playbooks and configurations to automate the setup of my development environments on both macOS and Linux.

## Quick Start

The setup process is primarily driven by `make` commands which wrap Ansible playbooks.

1.  **Bootstrap:** Run the appropriate bootstrap script for your OS. This installs essential dependencies like Ansible.
    *   **Ubuntu:** `./bootstrap/ubuntu.sh`
    *   **macOS:** `./bootstrap/darwin.sh`

2.  **Core System:** Install core tools and configure the system.
    ```bash
    make core
    ```

3.  **Terminal:** Configure the terminal environment (fish, tmux, vim, git, kitty).
    ```bash
    make term
    ```

4.  **Full Setup (Linux Only):** Apply a full machine setup based on its hostname.
    ```bash
    make setup
    ```
    This runs `make core` first, then applies machine-specific roles.

## Makefile Commands

*   `make core`: Runs the `core.yml` playbook to install essential tools and mount the NAS. This requires `sudo` and will prompt for a password.
*   `make nas`: Runs the `nas.yml` playbook to mount the NAS (macOS uses the current user with sudo privileges).
*   `make term`: Runs the `terminal.yml` playbook to configure the terminal environment.
*   `make setup`: (Linux only) Runs `make core` first, then runs `setup.yml` to apply machine-specific configuration based on the hostname.
*   `make backup`: Ensures the NAS is mounted, then backs up the `~/wip` directory to the NAS.

## Ansible Structure

The configuration is managed by Ansible playbooks and roles.

### Playbooks

*   `core.yml`: The main playbook for core system setup. Installs `core-tools` and mounts the NAS.
*   `terminal.yml`: Configures the terminal environment using the `terminal` role.
*   `setup.yml`: A Linux-only playbook that dynamically applies roles based on the machine's hostname. The hostname-to-role mapping is defined in `machines.yml`.

### Roles

*   `core-tools`: Installs common command-line tools, coding agents, and configures the kitty terminal.
*   `nas-mount`: Mounts the network-attached storage.
*   `sway-desktop`: Sets up the Sway tiling window manager and related tools for a graphical Linux environment.
*   `godot`: Installs the Godot Engine editor binary from https://godotengine.org/download (no extra runtime dependencies; bring your own editor/IDE).
*   `terminal`: Configures fish, tmux, vim, git, and other terminal applications.

### Configuration

*   `machines.yml`: Defines which roles to apply to which machine based on hostname patterns.
*   `group_vars/all/theme.yml`: Contains a centralized color scheme used across various applications like kitty and Waybar.
