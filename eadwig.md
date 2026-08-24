# Eaadwig deployment record

Eaadwig is deliberately deferred. Nothing in the current `openmw` role installs
the game, imports its saves, or exposes it through Sunshine. This file records
the validated private package and the contract to use if deployment is approved
later.

## Validated private package

- Archive: `/usr/local/mnt/iceburg/backup/rocks.smeg/wip/eaadwig/dist/eaadwig-0.1.0-private.tar.gz`
- Size: 39,615,015 bytes
- SHA-256: `866621493f73ef62e37e1bc7623bfeda6189673b1bf66b85e7e02ccf2f8db569`
- Source revision: `46219249d219791e4c6ee3d991a2c448e8077135`
- Archive root: `eaadwig-0.1.0-private/`
- Runtime requirement: OpenMW 0.51.x on Linux
- The archive's complete `MANIFEST.sha256` was verified successfully.

The packaged data tree contains 694 files and 105,825,935 bytes. Its structural
path-and-size digest is
`bc1a7adcb6cc6ac71495ef5b26e67913c63a0a7bfe2a748a0c1711254c7fef68`.
Critical content hashes are:

| File | SHA-256 |
| --- | --- |
| `data/eadwig.omwgame` | `71116b697dc2879b25fe8313a0018e232f22b5b72243110e4616373a5d071efe` |
| `data/eadwig.omwscripts` | `f216d579ce5864f84ef36f7b247b4cfb059ca7acb7b6ed08ec6406dae1200dda` |
| `data/abbot_slice.omwaddon` | `fc0a4a0c7c88d6d5ca47e9b9e6ebc8e0be3533971b92028c96237f59b67b9a95` |
| `data/thin_slice.omwaddon` | `63a56610e49f19f3e903929bd1cf3ca1011ba8d58ab08acb2a564d2db92d4914` |

The validated launcher enables only `eadwig.omwgame` followed by
`eadwig.omwscripts`. The two `.omwaddon` files are packaged but are not in the
validated load order; do not enable them without a new gameplay validation.

## Recoverable saves

The only unique saves found are under the archived Hal profile:

| Source | SHA-256 |
| --- | --- |
| `/usr/local/mnt/iceburg/backup/hal.smeg/wip/mw/eadwig/user-data/saves/ - 1/Autosave.omwsave` | `2e1f46c9b812040a1dade4b9e5f2b3abdee56b51953f8b0cc4c3bfdb158ce2f2` |
| `/usr/local/mnt/iceburg/backup/hal.smeg/wip/mw/eadwig/user-data/saves/ - 2/Quicksave.omwsave` | `822645435a087fb7ba07ea84b82e07bbb34af0d064d4bea605b2293d088674de` |

Preserve the names byte-for-byte during import. Do not import archived navmesh,
logs, screenshots, GUI storage, console history, shader caches, or smoke-test
output; OpenMW should regenerate them.

## Future installation contract

- Immutable package: `/opt/games/eaadwig/0.1.0-private`
- Selected package link: `/opt/games/eaadwig/current`
- OpenMW binary: `/opt/games/openmw/current/bin/openmw`
- OpenMW resources: `/opt/games/openmw/current/share/games/openmw/resources`
- Writable root: `/var/lib/sunshine-host/games/eaadwig`
- Mutable config: `/var/lib/sunshine-host/games/eaadwig/config`
- Saves and screenshots: `/var/lib/sunshine-host/games/eaadwig/user-data`
- Local generated data: `/var/lib/sunshine-host/games/eaadwig/data-local`
- Cache: `/var/cache/sunshine-host/games/eaadwig`
- Future launcher: `/usr/lib/sunshine-host/bin/run-eaadwig-openmw.sh`

The future launcher must call the immutable OpenMW binary directly. It must use
the runtime `vfs` and `vfs-mw` data directories first, then
`/opt/games/eaadwig/current/data`, followed by the exact validated content order
`eadwig.omwgame`, `eadwig.omwscripts`. Preserve the package's movie fallbacks,
`Scriptorium` start cell, and menu skip. Seed mutable settings only when absent.

## Licensing and privacy boundary

The archive contains recovered Morrowind and third-party mod assets. It is for
private use on authorised machines and must not be redistributed publicly. Keep
the archive, extracted assets, saves, credentials, and runtime state out of this
repository. Never import `nexus.cred` from the system backup. Only public
provisioning logic, checksums, and this inventory belong in `setup-system`.

## Re-enable checklist

1. Confirm the machine is authorised to use every packaged asset.
2. Verify the archive SHA-256 and every entry in its internal manifest.
3. Extract into the versioned immutable path and atomically select `current`.
4. Verify `/opt/games/openmw/current` is the approved OpenMW 0.51.x build.
5. Create the separate writable directories above as the Sunshine service user.
6. Seed package settings only when the mutable config is absent.
7. Import the two saves with their recorded hashes; do not import generated state.
8. Implement the direct launcher with the exact data and content order above.
9. Smoke-test locally, then through Sunshine with a controller attached.
10. Add the Sunshine application only after the smoke test passes, and verify a
    second Ansible run is convergent.
