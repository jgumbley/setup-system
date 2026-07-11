# System Setup

This repository contains Ansible playbooks and configurations to automate the setup of my development environments on both macOS and Linux.

## Quick Start

The setup process is primarily driven by `make` commands which wrap Ansible playbooks.

1.  **Bootstrap:** Run the appropriate bootstrap script for your OS. This installs essential dependencies like Ansible.
    *   **Ubuntu:** `./bootstrap/ubuntu.sh`
    *   **macOS:** `./bootstrap/darwin.sh`

2.  **Updates:** Quickly refresh coding agents, shared command-line tools, 1Password CLI, and other fast-moving essentials.
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
    This runs `make updates` first, then applies machine-specific roles.

## Makefile Commands

*   `make updates`: Runs the quick shared-tool refresh in `updates.yml`. This requires privilege escalation and may prompt for a password.
*   `make nas`: Runs the `nas.yml` playbook to mount the NAS (macOS uses the current user with sudo privileges).
*   `make term`: Runs the `terminal.yml` playbook to configure the terminal environment.
*   `make setup`: Runs `make updates` first, then runs `setup.yml` to fully converge the local machine using its exact hostname.
*   `make backup`: Ensures the NAS is mounted, then backs up the `~/wip` directory to the NAS.

## Ansible Structure

The configuration is managed by Ansible playbooks and roles.

### Playbooks

*   `updates.yml`: Refreshes shared foundational tools through `core-tools` and the 1Password CLI.
*   `terminal.yml`: Configures the terminal environment using the `terminal` role.
*   `setup.yml`: Applies roles selected by the machine's exact hostname. The hostname-to-role mapping is defined in `machines.yml`.

### Roles

*   `core-tools`: Installs common command-line tools, coding agents, and configures the kitty terminal.
*   `nas-mount`: Mounts the network-attached storage.
*   `sway-desktop`: Sets up the Sway tiling window manager and related tools for a graphical Linux environment.
*   `godot`: Installs the Godot Engine editor binary from https://godotengine.org/download (no extra runtime dependencies; bring your own editor/IDE).
*   `terminal`: Configures fish, tmux, vim, git, and other terminal applications.

### Configuration

*   `machines.yml`: Defines which roles to apply to each exact hostname.
*   `group_vars/all/theme.yml`: Contains a centralized color scheme used across various applications like kitty and Waybar.
