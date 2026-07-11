# Setup-System Refactor and Machine Roadmap

This is the authoritative execution plan for the current milestone. It is
deliberately ordered so that each code change can be tested and committed by the
operator before the next change begins.

## Execution protocol

- Read `AGENTS.md` and the root `Makefile`, then run `make digest`, before doing
  any work.
- Use Make as the entry point for every runtime command and test.
- Preserve the existing architecture: local Ansible against `localhost`, with
  hostname-selected roles. Do not introduce a controller, remote inventory, or
  fleet orchestration.
- Implement **only one numbered change per context**.
- Start each change from a clean working tree containing the operator's commit
  of the previous change.
- Run the stated verification, report the diff and results, and stop. Do not
  commit; the operator will test and commit.
- Do not begin the next numbered change automatically.
- **Do not begin step 5 or any work from step 6 onward until remaining changes
  3–4 have each been implemented, tested, and committed in order.**
- Do not add generalized validation, platform-detection frameworks, fallback
  behavior, or optional feature toggles. Solve only the concrete issues below.

## Current architectural intent

- `make updates` is the quick, frequently-run refresh path for coding agents,
  shared command-line tools, 1Password CLI, and other fast-moving essentials.
- `make setup` is the comprehensive machine converger. It runs `updates` first,
  then applies the roles selected for the current hostname.
- Heavy or machine-specific software such as OpenMW belongs in hostname roles,
  not in `updates`.
- Ubuntu and macOS continue to share the repository. Existing per-role
  Ubuntu/Darwin task and variable separation remains in place; this milestone
  does not redesign it.
- `pane.sh` intentionally does not need an executable bit. Where Make needs the
  helper, it is invoked with `bash pane.sh`; do not change its mode merely to
  permit direct execution.

---

## Change 3 — OpenMW convergence and `rocks`

### Goal

Stop OpenMW from being removed and reinstalled on every convergence, preserve
the intended daily-build channel, and include OpenMW on `rocks`.

### Required implementation

1. Fix the OpenMW role.
   - Remove the opening task that purges distro/OpenMW packages on every run.
   - Keep both PPAs:
     - `ppa:openmw/openmw`
     - `ppa:openmw/openmw-daily`
   - The daily PPA depends on packages from the stable PPA, so neither is
     redundant.
   - After configuring both PPAs, install or upgrade the OpenMW packages using
     normal APT convergence (`state: latest`) rather than absent-then-present
     churn.
   - Keep the existing content-creation toolchain installed by the role.
   - Preserve the Sunshine/uinput block restricted to hostname `hal`; it must
     not run on `rocks` or `system`.

2. Add `openmw` to the `rocks` role list after `sway-desktop`.
   - The resulting `rocks` roles are:
     - `terminal`
     - `sway-desktop`
     - `openmw`
   - Shared `updates` work is supplied by `make setup` and is not duplicated in
     the machine list.

### Explicit non-goals

- Do not split runtime and content-creation packages into optional branches.
- Do not change HAL hardware, ROCm, Steam, or other game roles.
- Do not change backup or Ubuntu upgrade behavior.

### Verification

- Run `make setup-check`.
- Run `make setup` on `system` through the required pane workflow.
- Confirm the selected OpenMW package candidate comes from the intended PPA
  chain and OpenMW launches.
- Run `make setup` a second time and confirm OpenMW is not purged, removed,
  downgraded, or reinstalled unnecessarily.
- Confirm `rocks` resolves to `terminal`, `sway-desktop`, and `openmw`.

### Stop point

Report the changed files and verification results. Stop for operator testing and
commit before starting change 4.

---

## Change 4 — Reusable verified backup

### Goal

Enhance `make backup` into a reusable, host-keyed rolling backup for ordinary
future use. It is not an Ubuntu-upgrade target and must not contain upgrade
logic.

### Backup contract

- Retain `backup: nas` so the NAS is mounted and verified before copying data.
- Retain the host-specific root:
  `/usr/local/mnt/iceburg/backup/<hostname>.smeg/`.
- Use one rolling destination per host; do not create dated full snapshots.
- Back up:
  - `~/wip/`, including `/home/system/wip/models` when run locally on `hal`.
  - Critical user identity/environment state needed to recover the account,
    specifically `~/.ssh/` and `~/.secret_env`.
  - A generated host-state manifest under the host backup root.
- Preserve permissions and timestamps while retaining the current policy of not
  attempting to preserve the source group on the NAS.
- Continue excluding transient project data such as `node_modules`, Python
  virtual environments, `__pycache__`, and `.DS_Store` from the WIP mirror.
- Do not back up the complete home directory.
- Do not include phone data; `make backup-phone` remains separate.

### Host-state manifest

Overwrite one current manifest per host on every successful backup. It must
record enough information to rebuild or audit the machine without embedding
secret contents:

- Timestamp, hostname, OS release, kernel, and architecture.
- Installed/manual package inventory and configured package repositories.
- Snap and Flatpak inventory where those managers are installed.
- Enabled service inventory appropriate to the host OS.
- Docker container and volume names where Docker is installed; this is metadata
  only and does not claim to back up Docker volume contents.
- On macOS, record Homebrew formulae, casks, and services instead of Linux
  package/service data.

Missing optional package managers must be recorded as absent rather than hidden
or replaced with another source of truth.

### Verification behavior

- `make backup` must fail if NAS mounting, any declared source copy, manifest
  generation, or verification fails.
- After copying, perform a read-only source-to-destination verification that
  detects missing or different source files.
- Extra files already present in the rolling destination may remain; do not use
  deletion semantics that turn an accidental source deletion into immediate
  backup loss.
- Write/update a `last-success` record only after every copy and verification
  step succeeds.
- Do not add backup checks, markers, or dependencies to any Ubuntu upgrade
  workflow.

### Repository instruction alignment

- Keep all execution behind Make targets.
- Because NAS mounting, protected state, or Ansible temporary paths may require
  privileges or write outside the workspace, launch the public backup target
  through the documented Make/pane workflow.
- Keep `pane.sh` non-executable and invoke it through Bash where Make uses it.

### Verification

- Run `make backup` on `system` through the pane workflow.
- Confirm the rolling host destination contains:
  - the WIP mirror,
  - SSH and secret-environment state with protected permissions,
  - the current host-state manifest,
  - and `last-success`.
- Confirm manifest output contains package/service metadata but not secret file
  contents.
- Run the backup a second time and confirm it updates the same rolling
  destination successfully.
- Introduce a harmless source test file under a temporary WIP test directory,
  verify it copies, then remove the source test directory only after the backup
  behavior has been demonstrated. Do not use destructive cleanup on real data.

### Stop point

Report the changed files, exact backup destinations, and verification results.
Stop for operator testing and commit. Do not begin step 5 automatically.

---

## Step 5 — Apply backup to existing machines

This is an operational rollout of committed change 4, not another repository
change.

Run the committed `make backup` locally on:

1. `system`
2. `hal`
3. `arnold`

For each machine, confirm the WIP mirror, critical state, manifest, verification,
and `last-success` record. On `hal`, explicitly confirm that
`/home/system/wip/models` is present in the backed-up WIP mirror.

Do not commission either new machine until all three existing-machine backups
have succeeded and are readable.

---

## Step 6 — Commission greenfield Ubuntu 26.04 machines

These machines are clean installations, not Ubuntu upgrades.

### `legobrick`

- Install Ubuntu 26.04 and set the hostname exactly to `legobrick`.
- Clone this repository and run `make setup` locally. `setup` supplies
  `updates`, then applies `terminal`, `ssh_host`, and `realtime-audio`.
- Verify terminal configuration, key-only SSH, the `system` user, authorized
  keys, JACK, realtime permissions, attached audio devices, and the low-latency
  kernel.
- Prefer Ubuntu packages for Python audio dependencies on 26.04 rather than an
  unmanaged global pip installation. Fail if the required packages are not
  available; do not add a fallback environment.
- Run setup twice and confirm convergence.

### `rocks`

- Install Ubuntu 26.04 and set the hostname exactly to `rocks`.
- Clone this repository and run `make setup` locally. `setup` supplies
  `updates`, then applies `terminal`, `sway-desktop`, and `openmw`.
- Verify Sway, display/input/networking, terminal configuration, Mozilla deb
  Firefox, 1Password browser integration, retained Snap support, OpenMW, and the
  content-creation applications.
- Run setup twice and confirm Firefox and OpenMW do not churn.

---

## Step 7 — Inspect `models` and ROCm locally on `hal`

The `models` repository exists on `hal`, not on `system`. Do not infer its
absence or ownership from the `system` filesystem.

When working locally on `hal`:

1. Read `/home/system/wip/models/AGENTS.md` if present and its Makefile first,
   then run its sanctioned digest target.
2. Inventory its ROCm repositories, packages, driver/kernel assumptions,
   environment, llama.cpp/model builds, GPU targets, and verification.
3. Compare it with this repository's orphaned `inference` role and disabled
   ROCm block in `hal_hardware`.
4. Decide ownership from evidence:
   - `setup-system` should own operating-system repositories, ROCm packages,
     permissions, environment, and machine-level verification when appropriate.
   - `models` should own model runtimes, application builds, models, and
     application-specific configuration.
   - `hal_hardware` should own only HAL-specific hardware tuning.
5. Remove or move implementation only after that audit. Do not delete the
   existing inference material before inspecting the actual `models` repo.

AMD's current compatibility matrix does not list Ubuntu 26.04 for ROCm. Treat
that as a HAL migration constraint until official support or an explicit
operator decision changes it:
https://rocm.docs.amd.com/en/latest/compatibility/compatibility-matrix.html

---

## Step 8 — Design the generic Ubuntu upgrade workflow

This work is deliberately deferred until after both greenfield machines are
running. It is not part of changes 1–4.

Add host-neutral local Make targets with names that clearly belong to Ubuntu
release upgrades:

- `ubuntu-upgrade-check`
- `ubuntu-upgrade`
- `ubuntu-upgrade-verify`

Requirements:

- Do not hardcode `system` or `hal` into target names or implementation.
- Do not invoke, depend on, or inspect `make backup`; backup remains independent.
- `ubuntu-upgrade-check` assesses the current Ubuntu release, APT/dpkg health,
  complete current-release updates, pending reboot, disk space, third-party
  repositories, and normal stable upgrade availability.
- `ubuntu-upgrade` runs Canonical's interactive `do-release-upgrade` through the
  Make-owned pane workflow. Do not automate configuration-file decisions and do
  not provide fallback upgrade paths.
- `ubuntu-upgrade-verify` confirms the target release and package/repository
  health, then reapplies `make setup` and reports host-specific failures.

---

## Step 9 — Upgrade `system`

- Use the generic Ubuntu workflow on `system` before HAL because `system` has no
  ROCm dependency.
- Use Canonical's normal stable LTS upgrade path available at execution time;
  do not preserve an early-development-release flag in permanent automation.
- After reboot, verify Sway, networking, NAS, Mozilla deb Firefox and 1Password,
  OpenMW, emulators, Godot, Moonlight, backlight, firmware behavior, terminal
  tooling, and coding agents.
- Run `make setup` again to prove convergence.

---

## Step 10 — Decide and execute the HAL migration

Use the completed `models`/ROCm audit, AMD's then-current support matrix, and
evidence from `system` before choosing HAL's path.

Possible operator decisions are to keep HAL on its supported Ubuntu release,
perform a supported in-place upgrade, or reinstall from bare metal once the
required ROCm stack supports the target release. Do not encode multiple HAL
paths in the repository. Make the decision first, then implement only the
selected path.

Before destructive HAL work, verify the committed reusable backup contains the
WIP/models repository and other critical state, and separately account for
Docker volume data, SSH host identity, OpenMW/Steam data, secrets, and inference
state required for restoration.

---

## Persistent boundaries

- `arnold` remains macOS and is excluded from Ubuntu release upgrades.
- `backup-phone` remains separate from host backup.
- No central controller, remote fleet inventory, or orchestration layer.
- All provisioning, backup, verification, and upgrades remain local and
  Make-driven.
