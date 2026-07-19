#!/usr/bin/env python3
import json
import pathlib
import sys


def walk(value):
    if isinstance(value, dict):
        keys = {str(key).lower() for key in value}
        if {"name", "uuid"} & keys or {"hostname", "uuid"} & keys:
            yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: sunshine_pairings_status.py <sunshine-state-dir>", file=sys.stderr)
        return 2

    root = pathlib.Path(sys.argv[1])
    shown = False

    state_paths = [root / "sunshine_state.json"]
    state_paths.extend(path for path in sorted(root.rglob("*state*.json")) if path not in state_paths)

    for path in state_paths:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text())
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue

        for entry in walk(data):
            name = (
                entry.get("name")
                or entry.get("hostname")
                or entry.get("device_name")
                or entry.get("uuid")
                or "client"
            )
            uuid = entry.get("uuid") or entry.get("uniqueid") or entry.get("id") or ""
            suffix = f" ({uuid})" if uuid else ""
            print(f"  {path}: {name}{suffix}")
            shown = True

    if not shown:
        print("  no client entries recognized; pairings may be in Sunshine certificate/state files.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
