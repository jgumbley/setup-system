# ROCKNIX ROM and save storage

Use `/usr/local/mnt/iceburg/roms/` as the canonical ROM and save tree on
Iceburg. `/usr/local/mnt/iceburg` resolves to the Iceburg mount at
`/mnt/iceburg`, so both paths refer to the same storage; repository manifests
and instructions should use the `/usr/local/mnt/iceburg` form consistently.

The contents of this directory mirror ROCKNIX's
`STORAGE/games-internal/roms/` directory:

```text
/usr/local/mnt/iceburg/roms/
├── snes/
│   ├── EarthBound (USA).sfc
│   ├── EarthBound (USA).srm
│   └── EarthBound (USA)--8bebad6c34a9d5e1.srm
└── savestates/
    └── snes/
        ├── EarthBound (USA).state.auto
        ├── EarthBound (USA).state.auto.png
        ├── EarthBound (USA).state1
        └── EarthBound (USA).state1.png
```

Keep every ROM in its ROCKNIX system directory, using names such as `snes`,
`gba`, `megadrive`, and `fbneo`. Battery-backed SRAM saves and savestates use
different locations and must not be mixed together.

## SRAM saves

The active SRAM save sits beside its ROM and uses the exact bare ROM stem. For
example, `EarthBound (USA).sfc` loads `EarthBound (USA).srm`. This bare name is
the save that ROCKNIX and RetroArch pick up automatically.

Keep each older, distinct save beside the active save as:

```text
<ROM stem>--<first 16 hexadecimal characters of its SHA-256>.srm
```

Call a save active only when it is the known most-progressed save or has been
explicitly selected. Do not choose it from modification time alone: copying or
restoring a file can give an older playthrough a newer timestamp. Exact
duplicates need only one copy.

To activate an archived save:

1. Archive the current bare `.srm` under its own hash name if that content is
   not already preserved.
2. Copy the selected archived save to the exact bare `<ROM stem>.srm` name.
3. Verify the copied content before removing or replacing anything elsewhere.

## Savestates

Store savestates under `roms/savestates/<system>/`. RetroArch uses these slot
names:

- `.state` for slot zero
- `.state1`, `.state2`, and so on for numbered slots
- `.state.auto` for the automatic state

If files with the same slot name have identical content, retain one. If their
content differs, keep the active or current state at its existing name and move
the other state to the next unused numbered slot. Treat an older conflicting
`.state.auto` the same way by moving it to the next unused numbered slot.

A state preview belongs to the state with the same stem. Whenever a state is
renumbered, rename its `.png` preview with it; for example, move both
`Game.state1` and `Game.state1.png` to `Game.state2` and `Game.state2.png`.

Before merging or restoring saves, compare file hashes. Never overwrite a
distinct SRAM save, state, or state preview until the existing content has been
preserved under these rules.
