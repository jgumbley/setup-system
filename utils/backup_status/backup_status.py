#!/usr/bin/env python3
import datetime
import pathlib
import sys


MARKER_NAME = ".last-successful-backup"


def format_timestamp(timestamp: float) -> str:
    return datetime.datetime.fromtimestamp(timestamp).astimezone().isoformat(
        sep=" ", timespec="seconds"
    )


def record(backup_path: pathlib.Path) -> int:
    if not backup_path.is_dir():
        print(f"Backup directory does not exist: {backup_path}", file=sys.stderr)
        return 1

    (backup_path / MARKER_NAME).touch()
    return 0


def status(backup_root: pathlib.Path) -> int:
    if not backup_root.is_dir():
        print(f"Backup root does not exist: {backup_root}", file=sys.stderr)
        return 1

    backups = sorted(
        path for path in backup_root.glob("*.smeg") if path.is_dir()
    )
    if not backups:
        print(f"No host backups found under {backup_root}", file=sys.stderr)
        return 1

    hosts = [path.name.removesuffix(".smeg") for path in backups]
    host_width = max(len("HOST"), *(len(host) for host in hosts))
    print(f"{'HOST':<{host_width}}  LAST SUCCESSFUL BACKUP")

    for host, backup_path in zip(hosts, backups):
        marker = backup_path / MARKER_NAME
        last_backup = (
            format_timestamp(marker.stat().st_mtime)
            if marker.is_file()
            else "not recorded"
        )
        print(f"{host:<{host_width}}  {last_backup}")

    return 0


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[1] not in {"record", "status"}:
        print(
            "usage: backup_status.py {record <host-backup-dir>|status <backup-root>}",
            file=sys.stderr,
        )
        return 2

    command = argv[1]
    path = pathlib.Path(argv[2])
    return record(path) if command == "record" else status(path)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
