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

## Next repository change — 1Password SSH workflow

Manage the native 1Password desktop application and SSH-agent integration on
graphical Ubuntu machines without changing or rotating existing SSH keys.

Requirements:

- Preserve the intentional `jg` and `tw` SSH aliases; `tw` is required on the
  work Mac even though its private key is not present on `system`.
- Use `jg` consistently for personal GitHub remotes.
- Keep the existing keypairs and public-key fingerprints. Do not rekey hosts or
  GitHub merely to adopt the 1Password agent.
- Install the native 1Password desktop package on graphical Ubuntu hosts that
  use Sway. Do not use the Snap or Flatpak build for this purpose because the
  SSH agent is required.
- Continue installing the 1Password CLI through the existing updates workflow.
- Manage the Linux 1Password agent socket in SSH client configuration without
  breaking the existing macOS `jg`/`tw` behavior.
- Never place private keys, account credentials, or automated 1Password sign-in
  material in this repository. Importing keys, signing in, and enabling the SSH
  agent remain manual commissioning actions.
- Keep public inbound-access keys managed by `ssh_host`.

Verification:

- On `system`, `ssh -T jg` authenticates to the personal GitHub account through
  the 1Password agent with the existing `system.pub` fingerprint.
- Personal repositories use the `jg` alias for fetch and push.
- Existing macOS alias behavior remains represented correctly in the shared
  SSH template.
- Running setup twice does not repeatedly reinstall or reconfigure 1Password.

Stop after verification for operator testing and commit.

## Commission `legobrick`

`legobrick` is a headless Ubuntu 26.04 machine administered remotely; coding
agents do not run there.

1. Install Ubuntu 26.04 and set the hostname exactly to `legobrick`.
2. Clone this public repository over HTTPS so the machine needs no GitHub
   private key.
3. Run `make setup` locally. It applies updates, `terminal`, `ssh_host`, and
   `realtime-audio`.
4. Verify the `system` user, key-only inbound SSH, authorized public keys, fish,
   JACK, realtime permissions, attached audio devices, and low-latency kernel.
5. From an administrative workstation, connect using the `jg` key held by the
   1Password agent.
6. For later maintenance, SSH into `legobrick`, attach to tmux, pull over HTTPS,
   and run `make setup` through `bash pane.sh`.
7. Run setup twice and confirm convergence.

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
