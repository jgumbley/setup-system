# Setup-System Roadmap

This plan contains only unfinished work. Completed implementation belongs in
the working tree and commit history, not here.

## Execution protocol

- Read `AGENTS.md` and the root `Makefile`, then run `make digest` before work.
- Use Make as the entry point for runtime commands and tests.
- Keep provisioning local to each machine and selected by exact hostname.
- Implement, verify, and commit one repository change before starting another.
- Run privileged or interactive Make targets through `bash pane.sh`.
- Do not add fallbacks, optional branches, or generalized validation.

## Commission `legobrick`

`legobrick` is a headless Ubuntu 26.04 machine administered remotely; coding
agents do not run there.

1. Install Ubuntu 26.04 and set the hostname exactly to `legobrick`.
2. Install `git` and `make` from Ubuntu packages.
3. Clone this public repository over HTTPS so the machine needs no GitHub
   private key.
4. Run `make setup` locally. Its bootstrap prerequisite installs Ansible before
   applying updates, `terminal`, `ssh_host`, and `realtime-audio`.
5. Verify the `system` user, key-only inbound SSH, authorized public keys, fish,
   JACK, realtime permissions, attached audio devices, and low-latency kernel.
6. From an administrative workstation, connect using the `jg` key held by the
   1Password agent.
7. For later maintenance, SSH into `legobrick`, attach to tmux, pull over HTTPS,
   and run `make setup` through `bash pane.sh`.
8. Run setup twice and confirm convergence.

Prefer Ubuntu packages for Python audio dependencies. Fail if required packages
are unavailable; do not add an unmanaged global pip fallback.

## Commission `rocks`

1. Install Ubuntu 26.04 and set the hostname exactly to `rocks`.
2. Clone this repository and run `make setup` locally.
3. Apply the manual 1Password sign-in and SSH-agent commissioning steps.
4. Verify Sway, display, input, networking, terminal configuration, Mozilla deb
   Firefox, 1Password browser integration, Snap support, OpenMW, and the
   content-creation applications.
5. Run setup twice and confirm Firefox and OpenMW do not churn.

## Inspect `models` and ROCm locally on `hal`

The `models` repository exists on `hal`, not on `system`.

1. Read `/home/system/wip/models/AGENTS.md` if present and its Makefile, then run
   its sanctioned digest target.
2. Inventory ROCm repositories, packages, driver and kernel assumptions,
   environment, llama.cpp/model builds, GPU targets, and verification.
3. Compare the evidence with this repository's orphaned `inference` role and
   disabled ROCm block in `hal_hardware`.
4. Keep operating-system repositories, packages, permissions, and machine-level
   verification in `setup-system`; keep runtimes, builds, models, and
   application configuration in `models`; keep only HAL hardware tuning in
   `hal_hardware`.
5. Move or remove implementation only after inspecting the actual repository.

Treat Ubuntu 26.04 as unsupported for HAL until AMD's current ROCm compatibility
matrix or an explicit operator decision says otherwise:
https://rocm.docs.amd.com/en/latest/compatibility/compatibility-matrix.html

## Design the generic Ubuntu upgrade workflow

Do this only after both greenfield machines are running.

Add host-neutral local Make targets:

- `ubuntu-upgrade-check`
- `ubuntu-upgrade`
- `ubuntu-upgrade-verify`

The check target assesses the release, APT/dpkg health, current-release updates,
pending reboot, disk space, third-party repositories, and stable upgrade
availability. The upgrade target runs Canonical's interactive
`do-release-upgrade` through the Make-owned pane workflow. Verification confirms
the target release and package/repository health, reapplies `make setup`, and
reports host-specific failures. Keep backup logic independent.

## Upgrade `system`

Use the generic Ubuntu workflow on `system` before HAL. After reboot, verify
Sway, networking, NAS, Mozilla deb Firefox and 1Password, OpenMW, emulators,
Godot, Moonlight, backlight, firmware behavior, terminal tooling, and coding
agents. Run setup again to prove convergence.

## Decide and execute the HAL migration

Use the completed `models`/ROCm audit, AMD's then-current support matrix, and
evidence from the `system` upgrade before choosing whether HAL remains on its
current release, receives a supported in-place upgrade, or is reinstalled.
Choose one path before implementing it; do not encode multiple paths.

## Persistent boundaries

- `arnold` remains macOS and is excluded from Ubuntu release upgrades.
- `backup-phone` remains separate from host backup.
- No central controller, remote fleet inventory, or orchestration layer.
- Provisioning and upgrades remain local and Make-driven.
