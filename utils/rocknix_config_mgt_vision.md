# ROCKNIX configuration-management vision

## Vision

Maintain small, curated ROCKNIX installations containing only the best games.
Iceburg is the canonical ROCKNIX-shaped source for ROMs, BIOS files, and game
data. It is needed while syncing; Holly and the handhelds keep local
distributions and must run without it. A distribution is a converged native
ROCKNIX tree, not a rebuilt image or snapshot.

## Operating model

- Ansible owns all configuration and curation data. Common policy and an
  explicitly selected low-power, high-power, or Holly profile produce the
  target configuration; the sync host does not choose the profile.
- Curation is declared per emulated system. Each declaration contains universal
  selections, named selections, and BIOS requirements. A selection names exact
  canonical ROCKNIX-relative files or complete game units. Adding a universal
  game makes it desired on every target that enables that system.
- The host-neutral sync utility combines a target's selections and profile,
  generates an `rsync` include filter, and converges one system at a time.
  Before adoption, runtime state is preserved outside that system's ROM
  directory; the directory then becomes wholly managed. Unselected files are
  not copied and deselected files are removed. Other systems remain untouched.
  The managed BIOS set is the union required by all adopted systems.
- ROCKNIX scans the physically curated target tree normally. Collections and
  gamelists may improve presentation, but never hide a fully copied library.
- Saves, states, memory cards, screenshots, caches, and logs are runtime state.
  Convergence preserves them; synchronising them is later scope.

The sync utility is shared. `utils/game_runtimes` continues to own Holly's
executable runtime, `roles/sunshine-host` its provisioning and launcher, and the
SD-card utilities their device checks, mounting, flashing, and flushing. These
target-specific parts call the same sync mechanism. Holly's local distribution
is the one launched by the existing Sunshine ROCKNIX application and streamed
through Moonlight; it is not a separate runtime or frontend.

## System slices

One agent session adopts one system. It may clean and curate that system on
Iceburg, define complete game units and BIOS requirements, develop Ansible
configuration for supported profiles, implement filtered sync, and verify real
targets. It records material discoveries here before the next slice begins.

## Milestones

1. **Holly/SNES:** create the shared sync utility and Holly's persistent local
   distribution. Move ROCKNIX configuration from launcher-time mutation into
   Ansible. Make the launcher use local content without Iceburg. Enable only
   SNES and copy only its selected games. Prove a no-change second sync, a
   one-ROM universal addition, safe deselection, preserved saves, and offline
   launch.
2. **Handheld SNES:** use the same curation, sync, and Ansible configuration for
   each handheld SD card. Flashing remains initial provisioning, not updating.
3. **ScummVM:** curate complete payloads and make registration and launch
   configuration deterministic.
4. **Dreamcast:** curate disc representations and bundles, BIOS requirements,
   and platform configuration.
5. **PS2:** clean its ROM and BIOS source, establish verified configuration,
   and curate games for capable targets.
6. **Remaining systems:** adopt one system per agent session.
7. **Save synchronisation:** design after content and configuration convergence
   is stable.
