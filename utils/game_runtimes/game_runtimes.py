#!/usr/bin/env python3
"""Pinned lifecycle operations for locally managed game runtimes."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import pwd
import re
import shlex
import shutil
import socket
import stat
import subprocess
import sys
import tarfile
import urllib.request


RUNTIME_MARKER = ".setup-system-runtime"
SOURCE_MARKER = ".setup-system-source"
BUILD_MARKER = ".setup-system-build"
IMPORT_MARKER = ".setup-system-import"
SNAPSHOT_MANIFEST = ".setup-system-snapshot.json"
SNAPSHOT_RE = re.compile(r"^[0-9]{8}T[0-9]{6}Z$")
KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
EXCLUDED_STATE_NAMES = frozenset({"navmesh.db", "mygui.log", "openmw.log"})
EXCLUDED_STATE_DIRS = frozenset({".cache", "cache", "logs"})


class ContractError(RuntimeError):
    """A deterministic repository or host contract was not satisfied."""


def fail(message: str) -> None:
    raise ContractError(message)


def load_manifest(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot read manifest {path}: {exc}")
    if not isinstance(data, dict):
        fail("manifest root must be an object")
    return data


def short_hostname() -> str:
    return socket.gethostname().split(".", 1)[0].lower()


def require_holly(manifest: dict) -> None:
    expected = manifest["host"]
    actual = short_hostname()
    if actual != expected:
        fail(f"this utility is Holly-only: expected host {expected!r}, got {actual!r}")


def require_openmw_host(manifest: dict) -> None:
    expected = manifest["openmw_hosts"]
    actual = short_hostname()
    if actual not in expected:
        fail(f"OpenMW is restricted to hosts {expected!r}, got {actual!r}")


def require_root() -> None:
    if os.geteuid() != 0:
        fail("this apply operation must run as root through its Make/pane target")


def command_exists(name: str) -> None:
    if shutil.which(name) is None:
        fail(f"required command is missing: {name}")


def run(
    argv: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    capture: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    print(f"+ {shlex.join(argv)}", flush=True)
    try:
        return subprocess.run(
            argv,
            cwd=str(cwd) if cwd else None,
            env=env,
            check=check,
            text=True,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
        )
    except FileNotFoundError:
        fail(f"required command is missing: {argv[0]}")
    except subprocess.CalledProcessError as exc:
        detail = ""
        if capture:
            detail = f": {(exc.stderr or exc.stdout or '').strip()}"
        fail(f"command failed ({exc.returncode}): {shlex.join(argv)}{detail}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        fail(f"cannot hash {path}: {exc}")
    return digest.hexdigest()


def fsync_file(path: Path) -> None:
    with path.open("rb") as stream:
        os.fsync(stream.fileno())


def fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_text(path: Path, text: str, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.setup-system-tmp")
    if temporary.exists() or temporary.is_symlink():
        fail(f"refusing stale temporary path: {temporary}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(temporary, flags, mode)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        fsync_dir(path.parent)
    except BaseException:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise


def write_kv_marker(path: Path, values: dict[str, str]) -> None:
    lines: list[str] = []
    for key, value in values.items():
        if not KEY_RE.fullmatch(key):
            fail(f"invalid marker key {key!r}")
        value = str(value)
        if "\n" in value or "\x00" in value:
            fail(f"invalid marker value for {key}")
        lines.append(f"{key}={shlex.quote(value)}\n")
    atomic_text(path, "".join(lines))


def read_kv_marker(path: Path) -> dict[str, str]:
    if not path.is_file() or path.is_symlink():
        fail(f"required marker is missing or invalid: {path}")
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        fail(f"cannot read marker {path}: {exc}")
    for number, line in enumerate(lines, 1):
        if not line or "=" not in line:
            fail(f"invalid marker line {path}:{number}")
        key, encoded = line.split("=", 1)
        if not KEY_RE.fullmatch(key) or key in values:
            fail(f"invalid or duplicate marker key {path}:{number}: {key!r}")
        try:
            parsed = shlex.split(encoded, posix=True)
        except ValueError as exc:
            fail(f"invalid shell value in {path}:{number}: {exc}")
        if len(parsed) != 1:
            fail(f"marker value must be one shell word in {path}:{number}")
        values[key] = parsed[0]
    return values


def require_marker(path: Path, expected: dict[str, str], *, exact: bool = True) -> dict[str, str]:
    actual = read_kv_marker(path)
    for key, value in expected.items():
        if actual.get(key) != str(value):
            fail(
                f"marker mismatch in {path}: {key} expected {str(value)!r}, "
                f"got {actual.get(key)!r}"
            )
    if exact and set(actual) != set(expected):
        fail(f"marker keys differ in {path}: expected {sorted(expected)}, got {sorted(actual)}")
    return actual


def runtime_marker(spec: dict, runtime: str) -> dict[str, str]:
    marker = source_marker(spec, runtime)
    marker["build_flags"] = spec["build_flags"]
    return marker


def source_marker(spec: dict, runtime: str) -> dict[str, str]:
    marker = {
        "runtime": runtime,
        "version": spec["version"],
        "revision": spec["revision"],
        "source_url": spec["url"],
        "source_sha256": spec["sha256"],
    }
    if "patch" in spec or "patch_sha256" in spec:
        if set(spec) >= {"patch", "patch_sha256"}:
            marker["patch"] = spec["patch"]
            marker["patch_sha256"] = spec["patch_sha256"]
        else:
            fail(f"runtime {runtime} has an incomplete patch contract")
    return marker


def build_marker(spec: dict, runtime: str) -> dict[str, str]:
    marker = source_marker(spec, runtime)
    marker["build_flags"] = spec["build_flags"]
    if "builder" in spec:
        marker["builder"] = spec["builder"]
    return marker


def safe_directory(path: Path, description: str) -> None:
    if not path.is_dir() or path.is_symlink():
        fail(f"{description} is missing or is not a real directory: {path}")


def safe_regular_file(path: Path, description: str, *, executable: bool = False) -> None:
    if not path.is_file() or path.is_symlink():
        fail(f"{description} is missing or is not a regular file: {path}")
    if executable and not os.access(path, os.X_OK):
        fail(f"{description} is not executable: {path}")


def validate_elf(path: Path, description: str) -> None:
    safe_regular_file(path, description, executable=True)
    try:
        with path.open("rb") as stream:
            magic = stream.read(4)
    except OSError as exc:
        fail(f"cannot inspect {description} {path}: {exc}")
    if magic != b"\x7fELF":
        fail(f"{description} is not an ELF executable: {path}")


def validate_elf_dependencies(path: Path, description: str) -> None:
    command_exists("ldd")
    result = run(["ldd", str(path)], capture=True, check=False)
    output = "\n".join((result.stdout, result.stderr))
    if result.returncode != 0:
        fail(f"cannot resolve shared libraries for {description} {path}: {output.strip()}")
    unresolved = [line.strip() for line in output.splitlines() if "not found" in line]
    if unresolved:
        fail(f"unresolved shared libraries for {description} {path}: {unresolved}")


def ensure_parent_not_symlink(path: Path) -> None:
    current = Path(path.anchor)
    for part in path.parts[1:-1]:
        current /= part
        if current.is_symlink():
            fail(f"refusing path below symlinked parent: {current}")


def install_paths(manifest: dict, runtime: str) -> tuple[Path, Path, Path]:
    spec = manifest["runtimes"][runtime]
    root = Path(manifest["install_root"]) / runtime
    final = root / spec["version"]
    current = root / "current"
    return root, final, current


def ensure_current(root: Path, version: str) -> None:
    current = root / "current"
    if current.exists() and not current.is_symlink():
        fail(f"refusing to replace non-symlink current path: {current}")
    temporary = root / ".current.setup-system-tmp"
    if temporary.exists() or temporary.is_symlink():
        fail(f"refusing stale current-link temporary path: {temporary}")
    os.symlink(version, temporary)
    os.replace(temporary, current)
    fsync_dir(root)


def verify_current(root: Path, version: str) -> None:
    current = root / "current"
    if not current.is_symlink():
        fail(f"required current symlink is missing: {current}")
    target = os.readlink(current)
    if target != version:
        fail(f"current symlink {current} must target {version!r}, got {target!r}")
    if current.resolve(strict=True) != (root / version).resolve(strict=True):
        fail(f"current symlink escapes its version directory: {current}")


def preflight_nas(manifest: dict) -> None:
    nas = manifest["nas"]
    alias = Path(nas["alias"])
    expected_target = Path(nas["target"])
    try:
        actual_target = alias.resolve(strict=True)
    except OSError as exc:
        fail(f"NAS alias is unavailable: {alias}: {exc}")
    if actual_target != expected_target:
        fail(f"NAS alias {alias} resolves to {actual_target}, expected {expected_target}")
    result = run(
        ["findmnt", "-rn", "-T", str(alias), "-o", "TARGET,SOURCE,FSTYPE"],
        capture=True,
    )
    matches = []
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) == 3:
            matches.append(tuple(fields))
    expected = (str(expected_target), nas["source"], nas["fstype"])
    if expected not in matches:
        fail(f"exact NAS mount {expected!r} not found; findmnt returned {matches!r}")


def walk_regular_files(root: Path, *, ignored_name: str | None = None) -> list[tuple[str, Path]]:
    safe_directory(root, "content tree")
    files: list[tuple[str, Path]] = []
    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        directory_path = Path(directory)
        for name in list(dirnames):
            candidate = directory_path / name
            if candidate.is_symlink():
                fail(f"symlinked directories are not permitted in validated trees: {candidate}")
        for name in filenames:
            if ignored_name and name == ignored_name:
                continue
            candidate = directory_path / name
            if candidate.is_symlink() or not candidate.is_file():
                fail(f"non-regular entries are not permitted in validated trees: {candidate}")
            relative = candidate.relative_to(root).as_posix()
            files.append((relative, candidate))
    files.sort(key=lambda item: item[0].encode("utf-8"))
    return files


def tree_stats(root: Path, *, ignored_name: str | None = None) -> tuple[int, int]:
    files = walk_regular_files(root, ignored_name=ignored_name)
    return len(files), sum(path.stat().st_size for _, path in files)


def tree_digest(root: Path, *, ignored_name: str | None = None) -> tuple[int, int, str]:
    digest = hashlib.sha256()
    files = walk_regular_files(root, ignored_name=ignored_name)
    total = 0
    for relative, path in files:
        size = path.stat().st_size
        total += size
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(size).encode("ascii"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(sha256_file(path)))
    return len(files), total, digest.hexdigest()


def validate_quake_content(spec: dict, root: Path) -> None:
    safe_directory(root, "Quake III baseq3 tree")
    actual_names = sorted(entry.name for entry in root.iterdir())
    expected_names = sorted(spec["files"])
    if actual_names != expected_names:
        fail(f"Quake III tree {root} must contain exactly pak0.pk3 through pak8.pk3")
    count, total = tree_stats(root)
    if count != spec["file_count"] or total != spec["bytes"]:
        fail(
            f"Quake III tree {root} has {count} files/{total} bytes; expected "
            f"{spec['file_count']} files/{spec['bytes']} bytes"
        )
    for relative, expected_hash in spec["files"].items():
        actual_hash = sha256_file(root / relative)
        if actual_hash != expected_hash:
            fail(f"Quake III hash mismatch for {root / relative}: {actual_hash}")


def validate_rocknix_content(spec: dict) -> None:
    root = Path(spec["root"])
    safe_directory(root, "ROCKNIX ROM root")
    system_directories = [
        entry for entry in root.iterdir() if entry.is_dir() and not entry.is_symlink()
    ]
    if not system_directories:
        fail(f"ROCKNIX ROM root contains no system directories: {root}")


def validate_morrowind_content(spec: dict, root: Path) -> None:
    safe_directory(root, "Morrowind data tree")
    count, total = tree_stats(root)
    if count != spec["file_count"] or total != spec["bytes"]:
        fail(
            f"Morrowind tree {root} has {count} files/{total} bytes; expected "
            f"{spec['file_count']} files/{spec['bytes']} bytes"
        )
    for relative, expected_hash in spec["required_files"].items():
        actual_hash = sha256_file(root / relative)
        if actual_hash != expected_hash:
            fail(f"Morrowind hash mismatch for {root / relative}: {actual_hash}")


def validate_mod_source(name: str, spec: dict) -> tuple[Path, int, int, str]:
    source = Path(spec["source"])
    safe_directory(source, f"{name} source")
    payload_name = spec["source_payload"]
    if payload_name == ".":
        payload = source
    else:
        entries = sorted(entry.name for entry in source.iterdir())
        if entries != [payload_name]:
            fail(
                f"{name} source must contain exactly its {payload_name!r} wrapper; got {entries!r}"
            )
        payload = source / payload_name
        safe_directory(payload, f"{name} normalized payload")
    count, total, digest = tree_digest(payload)
    if count != spec["file_count"]:
        fail(f"{name} source contains {count} files; expected {spec['file_count']}")
    if not any(relative.lower().endswith(".esp") for relative, _ in walk_regular_files(payload)):
        fail(f"{name} source contains no ESP plugin")
    return payload, count, total, digest


def copy_regular_tree(
    source: Path,
    destination: Path,
    *,
    exclude_state_cache: bool = False,
    owner: tuple[int, int] | None = None,
) -> None:
    safe_directory(source, "copy source")
    if destination.exists() or destination.is_symlink():
        fail(f"refusing to overwrite copy destination: {destination}")
    destination.mkdir(mode=stat.S_IMODE(source.stat().st_mode), parents=True)
    if owner:
        os.chown(destination, owner[0], owner[1])
    for directory, dirnames, filenames in os.walk(source, followlinks=False):
        src_dir = Path(directory)
        relative_dir = src_dir.relative_to(source)
        dst_dir = destination / relative_dir
        kept_dirs: list[str] = []
        for name in dirnames:
            src = src_dir / name
            if src.is_symlink():
                fail(f"refusing symlinked directory while copying state/content: {src}")
            if exclude_state_cache and name.lower() in EXCLUDED_STATE_DIRS:
                continue
            dst = dst_dir / name
            dst.mkdir(mode=stat.S_IMODE(src.stat().st_mode))
            if owner:
                os.chown(dst, owner[0], owner[1])
            else:
                try:
                    os.chown(dst, src.stat().st_uid, src.stat().st_gid)
                except PermissionError:
                    pass
            shutil.copystat(src, dst, follow_symlinks=False)
            kept_dirs.append(name)
        dirnames[:] = kept_dirs
        for name in filenames:
            src = src_dir / name
            if src.is_symlink() or not src.is_file():
                fail(f"refusing non-regular file while copying state/content: {src}")
            if exclude_state_cache and is_excluded_state_path(src.relative_to(source)):
                continue
            dst = dst_dir / name
            shutil.copy2(src, dst, follow_symlinks=False)
            if owner:
                os.chown(dst, owner[0], owner[1])
            else:
                try:
                    os.chown(dst, src.stat().st_uid, src.stat().st_gid)
                except PermissionError:
                    pass


def validate_quake_autoexec(manifest: dict) -> None:
    state = manifest["state_import"]
    source = Path(__file__).resolve().parent / state["quake3_autoexec_source"]
    destination = Path(state["quake3_baseq3"]) / "autoexec.cfg"
    safe_regular_file(source, "repository-managed Quake III autoexec source")
    safe_regular_file(destination, "managed Quake III autoexec destination")
    if sha256_file(destination) != sha256_file(source):
        fail(f"managed Quake III autoexec differs from its repository contract: {destination}")

def state_owner() -> tuple[int, int]:
    try:
        account = pwd.getpwnam("system")
    except KeyError:
        fail("required Sunshine account 'system' does not exist")
    return account.pw_uid, account.pw_gid


def is_excluded_state_path(relative: Path) -> bool:
    parts = [part.lower() for part in relative.parts]
    if any(part in EXCLUDED_STATE_DIRS for part in parts[:-1]):
        return True
    name = parts[-1] if parts else ""
    return name in EXCLUDED_STATE_NAMES or name.endswith(".log")


def selected_tree_digest(root: Path) -> tuple[int, int, str]:
    safe_directory(root, "state tree")
    digest = hashlib.sha256()
    count = 0
    total = 0
    for relative, path in walk_regular_files(root):
        relative_path = Path(relative)
        if is_excluded_state_path(relative_path):
            continue
        size = path.stat().st_size
        count += 1
        total += size
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(size).encode("ascii"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(sha256_file(path)))
    return count, total, digest.hexdigest()


def write_import_provenance(path: Path, component: str, source: Path, root: Path) -> None:
    count, total, digest = selected_tree_digest(root)
    write_kv_marker(
        path,
        {
            "component": component,
            "source": str(source),
            "source_tree_sha256": digest,
            "file_count": str(count),
            "bytes": str(total),
        },
    )


def validate_native_state_source(root: Path) -> None:
    safe_directory(root, "audited native OpenMW state source")
    safe_directory(root / "config", "audited native OpenMW config source")
    safe_directory(root / "user-data", "audited native OpenMW user-data source")
    safe_regular_file(root / "config" / "input_v3.xml", "native OpenMW controller configuration")


def selection_digest(files: list[tuple[str, Path]]) -> tuple[int, int, str]:
    digest = hashlib.sha256()
    total = 0
    for logical_name, path in sorted(files, key=lambda item: item[0].encode("utf-8")):
        safe_regular_file(path, f"selected state source {logical_name}")
        size = path.stat().st_size
        total += size
        digest.update(logical_name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(size).encode("ascii"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(sha256_file(path)))
    return len(files), total, digest.hexdigest()


def selected_source_files(root: Path, prefix: str = "") -> list[tuple[str, Path]]:
    selected: list[tuple[str, Path]] = []
    for relative, path in walk_regular_files(root):
        if is_excluded_state_path(Path(relative)):
            continue
        logical = f"{prefix}/{relative}" if prefix else relative
        selected.append((logical, path))
    return selected


def native_import_marker_values(source: Path) -> dict[str, str]:
    selected = [("config/input_v3.xml", source / "config" / "input_v3.xml")]
    selected.extend(selected_source_files(source / "user-data", "user-data"))
    count, total, digest = selection_digest(selected)
    return {
        "component": "morrowind-native",
        "source": str(source),
        "source_selection_sha256": digest,
        "file_count": str(count),
        "bytes": str(total),
    }


def merge_tree_without_overwrite(source: Path, destination: Path, owner: tuple[int, int]) -> int:
    """Merge absent files only after a complete collision preflight; preserve raw names."""
    safe_directory(source, "state merge source")
    destination_missing = not (destination.exists() or destination.is_symlink())
    if destination_missing:
        safe_directory(destination.parent, "Ansible-managed state destination parent")
    else:
        safe_directory(destination, "Ansible-managed state destination")
    directories: list[tuple[Path, Path]] = []
    files: list[tuple[Path, Path]] = []
    for directory, dirnames, filenames in os.walk(source, followlinks=False):
        src_dir = Path(directory)
        relative_dir = src_dir.relative_to(source)
        if is_excluded_state_path(relative_dir):
            dirnames[:] = []
            continue
        for name in list(dirnames):
            src = src_dir / name
            if src.is_symlink():
                fail(f"refusing symlinked state source directory: {src}")
            relative = src.relative_to(source)
            if is_excluded_state_path(relative):
                dirnames.remove(name)
                continue
            target = destination / relative
            if target.exists() or target.is_symlink():
                safe_directory(target, "existing state destination directory")
            directories.append((src, target))
        for name in filenames:
            src = src_dir / name
            relative = src.relative_to(source)
            if is_excluded_state_path(relative):
                continue
            if src.is_symlink() or not src.is_file():
                fail(f"refusing non-regular state source file: {src}")
            target = destination / relative
            if target.exists() or target.is_symlink():
                fail(f"refusing state import collision; destination file already exists: {target}")
            files.append((src, target))
    if destination_missing:
        destination.mkdir(mode=0o750)
        os.chown(destination, owner[0], owner[1])
    for src, target in sorted(directories, key=lambda item: len(item[1].parts)):
        if not target.exists():
            target.mkdir(mode=stat.S_IMODE(src.stat().st_mode))
            os.chown(target, owner[0], owner[1])
    for src, target in files:
        target.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        fd = os.open(target, flags, stat.S_IMODE(src.stat().st_mode))
        try:
            with src.open("rb") as input_stream, os.fdopen(fd, "wb") as output_stream:
                shutil.copyfileobj(input_stream, output_stream, length=1024 * 1024)
                output_stream.flush()
                os.fsync(output_stream.fileno())
            shutil.copystat(src, target, follow_symlinks=False)
            os.chown(target, owner[0], owner[1])
        except BaseException:
            try:
                target.unlink()
            except FileNotFoundError:
                pass
            raise
    return len(files)


def copy_file_if_absent(source: Path, destination: Path, owner: tuple[int, int]) -> bool:
    safe_regular_file(source, "state import source file")
    if destination.exists() or destination.is_symlink():
        safe_regular_file(destination, "existing managed state file")
        return False
    temporary = destination.with_name(f".{destination.name}.setup-system-stage")
    if temporary.exists() or temporary.is_symlink():
        fail(f"refusing stale state-file import stage: {temporary}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(temporary, flags, stat.S_IMODE(source.stat().st_mode))
    try:
        with source.open("rb") as input_stream, os.fdopen(fd, "wb") as output_stream:
            shutil.copyfileobj(input_stream, output_stream, length=1024 * 1024)
            output_stream.flush()
            os.fsync(output_stream.fileno())
        shutil.copystat(source, temporary, follow_symlinks=False)
        os.chown(temporary, owner[0], owner[1])
        try:
            os.link(temporary, destination, follow_symlinks=False)
        except FileExistsError:
            temporary.unlink()
            return False
        temporary.unlink()
        fsync_dir(destination.parent)
    except BaseException:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise
    return True


def validate_rocknix_state(manifest: dict) -> None:
    root = Path(manifest["state_import"]["rocknix_root"])
    safe_directory(root, "ROCKNIX mutable state root")
    for name in ("saves", "states", "screenshots"):
        safe_directory(root / name, f"ROCKNIX {name} state")


def validate_imported_state(manifest: dict) -> None:
    state = manifest["state_import"]
    native_source = Path(state["native_source"])
    validate_native_state_source(native_source)
    native_root = Path(state["native_root"])
    safe_directory(native_root, "Ansible-managed native OpenMW state root")
    require_marker(
        native_root / IMPORT_MARKER, native_import_marker_values(native_source)
    )
    for path in (
        Path(state["native_config"]),
        Path(state["native_user_data"]),
        Path(state["native_data_local"]),
    ):
        safe_directory(path, "native OpenMW imported state")
    for name in ("openmw.cfg", "settings.cfg"):
        safe_regular_file(Path(state["native_config"]) / name, f"Ansible-managed native {name}")

    quake_root = Path(state["quake3_root"])
    safe_directory(quake_root, "Quake III mutable state root")
    safe_directory(Path(state["quake3_baseq3"]), "Quake III mutable baseq3 state")
    autoexec_source = Path(__file__).resolve().parent / state["quake3_autoexec_source"]
    autoexec_destination = Path(state["quake3_baseq3"]) / "autoexec.cfg"
    safe_regular_file(autoexec_source, "repository-managed Quake III autoexec source")
    safe_regular_file(autoexec_destination, "managed Quake III autoexec destination")
    if sha256_file(autoexec_destination) != sha256_file(autoexec_source):
        fail(f"managed Quake III autoexec differs from its repository contract: {autoexec_destination}")
    validate_rocknix_state(manifest)


def import_state(manifest: dict) -> None:
    require_holly(manifest)
    require_root()
    preflight_nas(manifest)
    state = manifest["state_import"]
    owner = state_owner()
    state_root = Path(manifest["state_root"])
    safe_directory(state_root, "Ansible-managed game state root")
    native_root = Path(state["native_root"])
    native_config = Path(state["native_config"])
    native_user_data = Path(state["native_user_data"])
    native_data_local = Path(state["native_data_local"])
    rocknix_root = Path(state["rocknix_root"])
    quake_root = Path(state["quake3_root"])
    quake_baseq3 = Path(state["quake3_baseq3"])
    for path in (
        native_root,
        native_config,
        native_user_data,
        native_data_local,
        rocknix_root,
        quake_root,
        quake_baseq3,
    ):
        safe_directory(path, "required Ansible-managed state directory")
    for name in ("saves", "states", "screenshots"):
        safe_directory(rocknix_root / name, f"Ansible-managed ROCKNIX {name} state")
    for name in ("openmw.cfg", "settings.cfg"):
        safe_regular_file(native_config / name, f"Ansible-managed native {name}")

    validate_quake_autoexec(manifest)

    native_source = Path(state["native_source"])
    validate_native_state_source(native_source)
    native_marker = native_root / IMPORT_MARKER
    if native_marker.exists() or native_marker.is_symlink():
        require_marker(native_marker, native_import_marker_values(native_source))
        print("Native OpenMW legacy state was already imported; managed cfg/settings remain untouched")
    else:
        controller_added = copy_file_if_absent(
            native_source / "config" / "input_v3.xml", native_config / "input_v3.xml", owner
        )
        imported = merge_tree_without_overwrite(native_source / "user-data", native_user_data, owner)
        write_kv_marker(native_marker, native_import_marker_values(native_source))
        os.chown(native_marker, owner[0], owner[1])
        print(
            f"Imported {imported} native OpenMW user-data files; "
            f"controller config {'added' if controller_added else 'already present and left untouched'}"
        )

    native_cache = Path(manifest["state_cache_root"]) / "morrowind" / "native"
    safe_directory(native_cache, "Ansible-managed native OpenMW cache root")
    validate_imported_state(manifest)


def ensure_archive(manifest: dict, runtime: str) -> Path:
    spec = manifest["runtimes"][runtime]
    downloads = Path(manifest["cache_root"]) / "downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    archive = downloads / spec["archive"]
    if archive.exists() or archive.is_symlink():
        safe_regular_file(archive, f"cached {runtime} archive")
        actual = sha256_file(archive)
        if actual != spec["sha256"]:
            fail(f"cached {runtime} archive hash mismatch: {archive}: {actual}")
        return archive

    temporary = archive.with_name(f".{archive.name}.part")
    if temporary.exists() or temporary.is_symlink():
        fail(f"refusing stale partial download: {temporary}")
    source_url = spec["url"]
    try:
        if source_url.startswith("file:///"):
            local_source = Path(source_url.removeprefix("file://"))
            safe_regular_file(local_source, f"pinned local {runtime} archive")
            print(f"Copying pinned {runtime} archive: {local_source}", flush=True)
            with local_source.open("rb") as source, temporary.open("xb") as stream:
                shutil.copyfileobj(source, stream, length=1024 * 1024)
                stream.flush()
                os.fsync(stream.fileno())
        else:
            print(f"Downloading pinned {runtime} source: {source_url}", flush=True)
            request = urllib.request.Request(
                source_url,
                headers={"User-Agent": "setup-system-game-runtimes/1"},
            )
            with urllib.request.urlopen(request, timeout=120) as response, temporary.open("xb") as stream:
                shutil.copyfileobj(response, stream, length=1024 * 1024)
                stream.flush()
                os.fsync(stream.fileno())
        actual = sha256_file(temporary)
        if actual != spec["sha256"]:
            fail(f"downloaded {runtime} SHA256 mismatch: expected {spec['sha256']}, got {actual}")
        os.rename(temporary, archive)
        fsync_dir(downloads)
    except BaseException:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise
    return archive


def validate_tar_members(archive: tarfile.TarFile, expected_root: str) -> None:
    def normalized(parts: tuple[str, ...]) -> tuple[str, ...]:
        result: list[str] = []
        for part in parts:
            if part in ("", "."):
                continue
            if part == "..":
                if not result:
                    fail("archive link escapes its extraction root")
                result.pop()
            else:
                result.append(part)
        return tuple(result)

    prefix = expected_root + "/"
    for member in archive.getmembers():
        pure = PurePosixPath(member.name)
        if pure.is_absolute() or ".." in pure.parts:
            fail(f"unsafe path in source archive: {member.name!r}")
        if member.name != expected_root and not member.name.startswith(prefix):
            fail(f"unexpected top-level entry in source archive: {member.name!r}")
        if member.isdev() or member.isfifo():
            fail(f"unsupported special entry in source archive: {member.name!r}")
        if member.issym() or member.islnk():
            link = PurePosixPath(member.linkname)
            if link.is_absolute():
                fail(f"unsafe link in source archive: {member.name!r} -> {member.linkname!r}")
            if member.issym():
                target_parts = PurePosixPath(member.name).parent.parts + link.parts
            else:
                target_parts = link.parts
            resolved = normalized(target_parts)
            if not resolved or resolved[0] != expected_root:
                fail(f"archive link escapes source root: {member.name!r} -> {member.linkname!r}")


def ensure_source(manifest: dict, runtime: str) -> Path:
    spec = manifest["runtimes"][runtime]
    if "archive_root" not in spec:
        fail(f"runtime {runtime} has no source-tree contract")
    source_parent = Path(manifest["cache_root"]) / "sources" / runtime
    source = source_parent / spec["version"]
    expected = source_marker(spec, runtime)
    if source.exists() or source.is_symlink():
        safe_directory(source, f"cached {runtime} source")
        require_marker(source / SOURCE_MARKER, expected)
        return source
    archive_path = ensure_archive(manifest, runtime)
    source_parent.mkdir(parents=True, exist_ok=True)
    stage = source_parent / f".{spec['version']}.setup-system-extract"
    if stage.exists() or stage.is_symlink():
        fail(f"refusing stale {runtime} source extraction: {stage}")
    stage.mkdir()
    try:
        with tarfile.open(archive_path, mode="r:*") as archive:
            validate_tar_members(archive, spec["archive_root"])
            try:
                archive.extractall(stage, filter="data")
            except TypeError:
                archive.extractall(stage)
        extracted = stage / spec["archive_root"]
        safe_directory(extracted, f"extracted {runtime} source root")
        if "patch" in spec:
            patch_relative = PurePosixPath(spec["patch"])
            if patch_relative.is_absolute() or ".." in patch_relative.parts:
                fail(f"runtime {runtime} patch path escapes the utility: {spec['patch']!r}")
            patch_path = Path(__file__).resolve().parent / Path(*patch_relative.parts)
            safe_regular_file(patch_path, f"pinned {runtime} patch")
            actual_patch_sha256 = sha256_file(patch_path)
            if actual_patch_sha256 != spec["patch_sha256"]:
                fail(
                    f"pinned {runtime} patch digest mismatch: "
                    f"{actual_patch_sha256} != {spec['patch_sha256']}"
                )
            command_exists("patch")
            run(
                [
                    "patch",
                    "--batch",
                    "--forward",
                    "-d",
                    str(extracted),
                    "-p1",
                    "--input",
                    str(patch_path),
                ]
            )
        write_kv_marker(extracted / SOURCE_MARKER, expected)
        os.rename(extracted, source)
        stage.rmdir()
        fsync_dir(source_parent)
    except BaseException:
        if stage.exists() and not source.exists():
            shutil.rmtree(stage)
        raise
    return source


def build_dir_contract(manifest: dict, runtime: str) -> tuple[Path, bool]:
    spec = manifest["runtimes"][runtime]
    build_dir = Path(manifest["cache_root"]) / "build" / runtime / spec["version"]
    expected = build_marker(spec, runtime)
    if build_dir.exists() or build_dir.is_symlink():
        safe_directory(build_dir, f"{runtime} build cache")
        require_marker(build_dir / BUILD_MARKER, expected)
        return build_dir, True
    build_dir.parent.mkdir(parents=True, exist_ok=True)
    build_dir.mkdir()
    return build_dir, False


def validate_openmw_payload(root: Path, description: str) -> None:
    for name, binary_description in (
        ("openmw", "OpenMW binary"),
        ("openmw-launcher", "OpenMW launcher"),
        ("openmw-cs", "OpenMW content editor"),
    ):
        validate_elf(root / "bin" / name, binary_description)
    for name in ("org.openmw.launcher.desktop", "org.openmw.cs.desktop"):
        safe_regular_file(root / "share" / "applications" / name, f"{description} desktop entry {name}")
    for name in ("openmw.png", "openmw-cs.png"):
        safe_regular_file(root / "share" / "pixmaps" / name, f"{description} desktop icon {name}")


def validate_openmw_install(manifest: dict) -> None:
    runtime = "openmw"
    spec = manifest["runtimes"][runtime]
    root, final, _ = install_paths(manifest, runtime)
    safe_directory(final, "OpenMW install")
    require_marker(final / RUNTIME_MARKER, runtime_marker(spec, runtime))
    validate_openmw_payload(final, "OpenMW install")
    verify_current(root, spec["version"])


def build_openmw(manifest: dict) -> None:
    require_openmw_host(manifest)
    require_root()
    runtime = "openmw"
    spec = manifest["runtimes"][runtime]
    root, final, _ = install_paths(manifest, runtime)
    if final.exists() or final.is_symlink():
        validate_openmw_install(manifest)
        print(f"OpenMW {spec['version']} is already installed and exact")
        return
    for command in ("cmake", "ninja"):
        command_exists(command)
    source = ensure_source(manifest, runtime)
    safe_regular_file(source / "CMakeLists.txt", "OpenMW CMake contract")
    build_dir, built = build_dir_contract(manifest, runtime)
    if not built:
        run(
            [
                "cmake",
                "-S",
                str(source),
                "-B",
                str(build_dir),
                "-G",
                "Ninja",
                "-DCMAKE_BUILD_TYPE=Release",
                f"-DCMAKE_INSTALL_PREFIX={final}",
            ]
        )
        run(["cmake", "--build", str(build_dir), "--parallel"])
        write_kv_marker(build_dir / BUILD_MARKER, build_marker(spec, runtime))
    root.mkdir(parents=True, exist_ok=True)
    destdir = root / f".{spec['version']}.setup-system-destdir"
    if destdir.exists() or destdir.is_symlink():
        fail(f"refusing stale OpenMW install stage: {destdir}")
    destdir.mkdir()
    env = os.environ.copy()
    env["DESTDIR"] = str(destdir)
    run(["cmake", "--install", str(build_dir)], env=env)
    payload = destdir / final.relative_to("/")
    safe_directory(payload, "staged OpenMW install")
    validate_openmw_payload(payload, "staged OpenMW install")
    write_kv_marker(payload / RUNTIME_MARKER, runtime_marker(spec, runtime))
    os.rename(payload, final)
    shutil.rmtree(destdir)
    ensure_current(root, spec["version"])
    validate_openmw_install(manifest)


def validate_quake_payload(root: Path, description: str) -> None:
    for name in (
        "quake3e.x64",
        "quake3e_opengl_x86_64.so",
        "quake3e_vulkan_x86_64.so",
    ):
        artifact = root / name
        validate_elf(artifact, f"{description} {name}")
        validate_elf_dependencies(artifact, f"{description} {name}")


def validate_quake_install(manifest: dict) -> None:
    runtime = "quake3e"
    spec = manifest["runtimes"][runtime]
    root, final, _ = install_paths(manifest, runtime)
    ensure_parent_not_symlink(final)
    safe_directory(final, "Quake3e install")
    require_marker(final / RUNTIME_MARKER, runtime_marker(spec, runtime))
    validate_quake_payload(final, "installed Quake3e")
    verify_current(root, spec["version"])


def build_quake3(manifest: dict) -> None:
    require_holly(manifest)
    require_root()
    runtime = "quake3e"
    spec = manifest["runtimes"][runtime]
    root, final, _ = install_paths(manifest, runtime)
    ensure_parent_not_symlink(final)
    if final.exists() or final.is_symlink():
        validate_quake_install(manifest)
        print(f"Quake3e {spec['version']} is already installed and exact")
        return
    for command in ("make", "gcc", "ldd", "patch", "pkg-config", "strip"):
        command_exists(command)
    source = ensure_source(manifest, runtime)
    safe_regular_file(source / "Makefile", "Quake3e Makefile contract")
    build_dir, built = build_dir_contract(manifest, runtime)
    if not built:
        jobs = str(max(1, os.cpu_count() or 1))
        run(
            [
                "make",
                "-C",
                str(source),
                f"-j{jobs}",
                "release",
                "ARCH=x86_64",
                f"BUILD_DIR={build_dir}",
            ]
        )
        validate_quake_payload(build_dir / "release-linux-x86_64", "built Quake3e")
        write_kv_marker(build_dir / BUILD_MARKER, build_marker(spec, runtime))
    validate_quake_payload(build_dir / "release-linux-x86_64", "cached Quake3e")
    root.mkdir(parents=True, exist_ok=True)
    stage = root / f".{spec['version']}.setup-system-stage"
    if stage.exists() or stage.is_symlink():
        fail(f"refusing stale Quake3e install stage: {stage}")
    stage.mkdir()
    run(
        [
            "make",
            "-C",
            str(source),
            "install",
            "ARCH=x86_64",
            f"BUILD_DIR={build_dir}",
            f"DESTDIR={stage}",
        ]
    )
    validate_quake_payload(stage, "staged Quake3e")
    write_kv_marker(stage / RUNTIME_MARKER, runtime_marker(spec, runtime))
    os.rename(stage, final)
    ensure_current(root, spec["version"])
    validate_quake_install(manifest)


def parse_os_release(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    safe_regular_file(path, "ROCKNIX os-release")
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            fail(f"invalid os-release line {path}:{number}")
        key, encoded = line.split("=", 1)
        try:
            parsed = shlex.split(encoded)
        except ValueError as exc:
            fail(f"invalid os-release value {path}:{number}: {exc}")
        if len(parsed) != 1:
            fail(f"invalid os-release value {path}:{number}")
        values[key] = parsed[0]
    return values


def validate_rocknix_rootfs(rootfs: Path, spec: dict) -> None:
    safe_directory(rootfs, "ROCKNIX rootfs")
    validate_elf(rootfs / "usr" / "bin" / "emulationstation", "ROCKNIX EmulationStation")
    validate_elf(rootfs / "usr" / "bin" / "localedef", "ROCKNIX localedef")
    validate_elf(rootfs / "usr" / "bin" / "retroarch", "ROCKNIX RetroArch")
    safe_directory(rootfs / "usr" / "lib" / "libretro", "ROCKNIX libretro cores")
    safe_directory(
        rootfs / "usr" / "share" / "libretro" / "autoconfig",
        "ROCKNIX packaged controller profiles",
    )
    safe_regular_file(
        rootfs / "usr" / "config" / "emulationstation" / "es_systems.cfg",
        "ROCKNIX EmulationStation systems configuration",
    )
    safe_regular_file(
        rootfs / "usr" / "config" / "emulationstation" / "es_features.cfg",
        "ROCKNIX EmulationStation features configuration",
    )
    safe_regular_file(
        rootfs / "usr" / "config" / "SDL-GameControllerDB" / "gamecontrollerdb.txt",
        "ROCKNIX SDL controller database",
    )
    safe_regular_file(
        rootfs / "usr" / "share" / "i18n" / "charmaps" / "UTF-8.gz",
        "ROCKNIX UTF-8 charmap",
    )
    safe_regular_file(
        rootfs / "usr" / "share" / "i18n" / "locales" / "en_GB",
        "ROCKNIX en_GB locale source",
    )
    release = parse_os_release(rootfs / "etc" / "os-release")
    required = {
        "OS_NAME": "ROCKNIX",
        "BUILD_ID": spec["revision"],
        "HW_DEVICE": "AMD64",
        "HW_ARCH": "x86_64",
        "DISTRO_DEVICE": "AMD64",
    }
    for key, expected in required.items():
        if release.get(key) != expected:
            fail(
                f"ROCKNIX os-release {key} mismatch: expected {expected!r}, got {release.get(key)!r}"
            )
    release_file = rootfs / "etc" / "release"
    safe_regular_file(release_file, "ROCKNIX release identity")
    actual_release = release_file.read_text(encoding="utf-8").strip()
    expected_release = f"AMD64.x86_64-{spec['version']}"
    if actual_release != expected_release:
        fail(f"ROCKNIX /etc/release mismatch: expected {expected_release!r}, got {actual_release!r}")


def docker_image_id(image: str) -> str | None:
    result = run(
        ["docker", "image", "inspect", "--format", "{{.Id}}", image],
        capture=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
        fail(f"Docker returned an invalid image ID for {image}: {value!r}")
    return value


def import_rocknix_image(rootfs: Path, image: str) -> str:
    command_exists("tar")
    command_exists("docker")
    tar_command = [
        "tar",
        "--sort=name",
        "--numeric-owner",
        "--xattrs",
        "--acls",
        "-C",
        str(rootfs),
        "-cf",
        "-",
        ".",
    ]
    docker_command = ["docker", "import", "-", image]
    print(f"+ {shlex.join(tar_command)} | {shlex.join(docker_command)}", flush=True)
    tar_process = subprocess.Popen(tar_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert tar_process.stdout is not None
    docker_process = subprocess.Popen(
        docker_command,
        stdin=tar_process.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    tar_process.stdout.close()
    docker_stdout, docker_stderr = docker_process.communicate()
    tar_stderr = tar_process.stderr.read().decode("utf-8", errors="replace") if tar_process.stderr else ""
    tar_return = tar_process.wait()
    if tar_return != 0:
        fail(f"metadata-preserving ROCKNIX tar failed ({tar_return}): {tar_stderr.strip()}")
    if docker_process.returncode != 0:
        fail(f"Docker import failed ({docker_process.returncode}): {docker_stderr.strip()}")
    imported = docker_stdout.strip()
    if imported and not re.fullmatch(r"sha256:[0-9a-f]{64}", imported):
        fail(f"Docker import returned an invalid image ID: {imported!r}")
    image_id = docker_image_id(image)
    if image_id is None:
        fail(f"Docker import did not create required tag {image}")
    return image_id


def rocknix_marker(spec: dict, image_id: str) -> dict[str, str]:
    marker = runtime_marker(spec, "rocknix")
    marker["docker_image"] = spec["docker_image"]
    marker["docker_image_id"] = image_id
    return marker


def validate_rocknix_install(manifest: dict) -> None:
    runtime = "rocknix"
    spec = manifest["runtimes"][runtime]
    root, final, _ = install_paths(manifest, runtime)
    safe_directory(final, "ROCKNIX install")
    validate_rocknix_rootfs(final / "rootfs", spec)
    marker = read_kv_marker(final / RUNTIME_MARKER)
    expected_without_id = runtime_marker(spec, runtime)
    expected_without_id["docker_image"] = spec["docker_image"]
    for key, value in expected_without_id.items():
        if marker.get(key) != value:
            fail(f"ROCKNIX marker mismatch for {key}: expected {value!r}, got {marker.get(key)!r}")
    expected_keys = set(expected_without_id) | {"docker_image_id"}
    if set(marker) != expected_keys:
        fail(f"ROCKNIX marker keys differ: expected {sorted(expected_keys)}, got {sorted(marker)}")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", marker["docker_image_id"]):
        fail("ROCKNIX marker contains an invalid Docker image ID")
    actual_id = docker_image_id(spec["docker_image"])
    if actual_id != marker["docker_image_id"]:
        fail(
            f"ROCKNIX Docker tag resolves to {actual_id!r}, marker requires {marker['docker_image_id']!r}"
        )
    verify_current(root, spec["version"])


def install_or_repair_rocknix_image(manifest: dict, final: Path) -> None:
    spec = manifest["runtimes"]["rocknix"]
    marker_path = final / RUNTIME_MARKER
    if marker_path.exists() or marker_path.is_symlink():
        marker = read_kv_marker(marker_path)
        expected = runtime_marker(spec, "rocknix")
        expected["docker_image"] = spec["docker_image"]
        for key, value in expected.items():
            if marker.get(key) != value:
                fail(f"existing ROCKNIX marker mismatch for {key}")
        recorded = marker.get("docker_image_id")
        actual = docker_image_id(spec["docker_image"])
        if recorded and actual == recorded:
            return
    image_id = import_rocknix_image(final / "rootfs", spec["docker_image"])
    write_kv_marker(marker_path, rocknix_marker(spec, image_id))


def build_rocknix(manifest: dict) -> None:
    require_holly(manifest)
    require_root()
    runtime = "rocknix"
    spec = manifest["runtimes"][runtime]
    command_exists("docker")
    root, final, _ = install_paths(manifest, runtime)
    if final.exists() or final.is_symlink():
        safe_directory(final, "ROCKNIX install")
        validate_rocknix_rootfs(final / "rootfs", spec)
        install_or_repair_rocknix_image(manifest, final)
        ensure_current(root, spec["version"])
        validate_rocknix_install(manifest)
        print(f"ROCKNIX {spec['version']} is installed; Docker execution image is exact")
        return

    source = ensure_source(manifest, runtime)
    system_image = source / "target" / "SYSTEM"
    checksum_file = source / "target" / "SYSTEM.md5"
    safe_regular_file(system_image, "pinned ROCKNIX SYSTEM image")
    safe_regular_file(checksum_file, "pinned ROCKNIX SYSTEM checksum")
    checksum_fields = checksum_file.read_text(encoding="utf-8").strip().split()
    if checksum_fields != [spec["system_md5"], "target/SYSTEM"]:
        fail(f"ROCKNIX SYSTEM checksum contract differs: {checksum_fields!r}")
    output = source / "rootfs"
    build_dir = Path(manifest["cache_root"]) / "build" / runtime / spec["version"]
    marker_path = build_dir / BUILD_MARKER
    if build_dir.exists() or build_dir.is_symlink():
        safe_directory(build_dir, "ROCKNIX build marker directory")
        require_marker(marker_path, build_marker(spec, runtime))
        validate_rocknix_rootfs(output, spec)
    else:
        if output.exists() or output.is_symlink():
            fail(
                f"ROCKNIX rootfs output exists without its build marker: {output}; "
                "remove the partial cache explicitly before retrying"
            )
        command_exists("md5sum")
        command_exists("unsquashfs")
        system_md5 = run(["md5sum", str(system_image)], capture=True).stdout.split()[0]
        if system_md5 != spec["system_md5"]:
            fail(
                f"ROCKNIX SYSTEM MD5 mismatch: expected {spec['system_md5']}, got {system_md5}"
            )
        run(["unsquashfs", "-no-progress", "-d", str(output), str(system_image)])
        validate_rocknix_rootfs(output, spec)
        build_dir.mkdir(parents=True)
        write_kv_marker(marker_path, build_marker(spec, runtime))

    root.mkdir(parents=True, exist_ok=True)
    stage = root / f".{spec['version']}.setup-system-stage"
    if stage.exists() or stage.is_symlink():
        fail(f"refusing stale ROCKNIX install stage: {stage}")
    (stage / "rootfs").mkdir(parents=True)
    run(["cp", "-a", "--reflink=auto", f"{output}/.", str(stage / "rootfs")])
    validate_rocknix_rootfs(stage / "rootfs", spec)
    os.rename(stage, final)
    fsync_dir(root)
    install_or_repair_rocknix_image(manifest, final)
    ensure_current(root, spec["version"])
    validate_rocknix_install(manifest)


def clean_rocknix_cache(manifest: dict) -> None:
    require_holly(manifest)
    require_root()
    runtime = "rocknix"
    cache_root = Path(manifest["cache_root"])
    cache_parents = (
        cache_root / "sources" / runtime,
        cache_root / "build" / runtime,
    )
    removed = 0
    for cache_parent in cache_parents:
        ensure_parent_not_symlink(cache_parent)
        if not cache_parent.exists():
            continue
        safe_directory(cache_parent, "generated ROCKNIX cache parent")
        for target in sorted(cache_parent.iterdir()):
            if target.is_symlink():
                fail(f"refusing symlinked ROCKNIX cache target: {target}")
            safe_directory(target, "generated ROCKNIX cache target")
            shutil.rmtree(target)
            fsync_dir(cache_parent)
            print(f"Removed generated ROCKNIX cache: {target}")
            removed += 1
    if not removed:
        print("ROCKNIX source/build cache is already absent")


def build_all(manifest: dict) -> None:
    build_openmw(manifest)
    build_quake3(manifest)
    build_rocknix(manifest)
    verify(manifest)


def component_tree_manifest(root: Path) -> list[dict[str, object]]:
    safe_directory(root, "state component")
    entries: list[dict[str, object]] = []
    root_info = root.stat()
    entries.append(
        {
            "path": ".",
            "type": "directory",
            "mode": stat.S_IMODE(root_info.st_mode),
            "uid": root_info.st_uid,
            "gid": root_info.st_gid,
        }
    )
    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        directory_path = Path(directory)
        kept_dirs: list[str] = []
        for name in sorted(dirnames):
            path = directory_path / name
            relative_path = path.relative_to(root)
            if is_excluded_state_path(relative_path):
                continue
            if path.is_symlink() or not path.is_dir():
                fail(f"non-directory entry in state directory set: {path}")
            info = path.stat()
            entries.append(
                {
                    "path": relative_path.as_posix(),
                    "type": "directory",
                    "mode": stat.S_IMODE(info.st_mode),
                    "uid": info.st_uid,
                    "gid": info.st_gid,
                }
            )
            kept_dirs.append(name)
        dirnames[:] = kept_dirs
        for name in sorted(filenames):
            path = directory_path / name
            relative_path = path.relative_to(root)
            if is_excluded_state_path(relative_path):
                continue
            if path.is_symlink() or not path.is_file():
                fail(f"non-regular entry in state file set: {path}")
            info = path.stat()
            entries.append(
                {
                    "path": relative_path.as_posix(),
                    "type": "file",
                    "size": info.st_size,
                    "sha256": sha256_file(path),
                    "mode": stat.S_IMODE(info.st_mode),
                    "uid": info.st_uid,
                    "gid": info.st_gid,
                }
            )
    entries.sort(key=lambda item: (str(item["path"]).encode("utf-8"), str(item["type"])))
    return entries


def validate_snapshot_component(root: Path, expected: list[dict[str, object]]) -> None:
    actual = component_tree_manifest(root)
    if actual != expected:
        fail(f"snapshot component checksum/metadata manifest mismatch: {root}")


def backup_state(manifest: dict) -> None:
    require_holly(manifest)
    require_root()
    preflight_nas(manifest)
    validate_imported_state(manifest)
    snapshot_root = Path(manifest["snapshot_root"])
    snapshot_root.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    final = snapshot_root / timestamp
    stage = snapshot_root / f".{timestamp}.setup-system-stage"
    if final.exists() or final.is_symlink():
        fail(f"snapshot already exists for this UTC second: {final}")
    if stage.exists() or stage.is_symlink():
        fail(f"refusing stale snapshot stage: {stage}")
    stage.mkdir(mode=0o750)
    metadata: dict[str, object] = {
        "schema": 1,
        "snapshot": timestamp,
        "host": manifest["host"],
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "excluded_names": sorted(EXCLUDED_STATE_NAMES),
        "excluded_directories": sorted(EXCLUDED_STATE_DIRS),
        "components": {},
    }
    components = metadata["components"]
    assert isinstance(components, dict)
    for component, source_text in manifest["backup_components"].items():
        source = Path(source_text)
        safe_directory(source, f"{component} state source")
        destination = stage / component
        copy_regular_tree(source, destination, exclude_state_cache=True)
        entries = component_tree_manifest(destination)
        components[component] = {"source": source_text, "entries": entries}
    manifest_text = json.dumps(metadata, indent=2, sort_keys=True) + "\n"
    atomic_text(stage / SNAPSHOT_MANIFEST, manifest_text, mode=0o640)
    os.rename(stage, final)
    fsync_dir(snapshot_root)
    print(f"Created verified game-state snapshot {final}")


def validate_restore_request(manifest: dict, snapshot: str, component: str, confirm_host: str) -> None:
    require_holly(manifest)
    if not SNAPSHOT_RE.fullmatch(snapshot):
        fail("SNAPSHOT must be an exact UTC basename in YYYYMMDDTHHMMSSZ form")
    if component not in manifest["backup_components"]:
        fail(
            f"COMPONENT must be exactly one of: {', '.join(sorted(manifest['backup_components']))}"
        )
    if confirm_host != manifest["host"]:
        fail(f"CONFIRM_HOST must be exactly {manifest['host']!r}")


def load_snapshot(manifest: dict, snapshot: str) -> tuple[Path, dict]:
    snapshot_root = Path(manifest["snapshot_root"])
    root = snapshot_root / snapshot
    safe_directory(root, "requested snapshot")
    marker = root / SNAPSHOT_MANIFEST
    safe_regular_file(marker, "snapshot manifest")
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot parse snapshot manifest {marker}: {exc}")
    if data.get("schema") != 1 or data.get("snapshot") != snapshot or data.get("host") != manifest["host"]:
        fail(f"snapshot identity does not match request: {marker}")
    if data.get("excluded_names") != sorted(EXCLUDED_STATE_NAMES):
        fail(f"snapshot exclusion contract differs: {marker}")
    if data.get("excluded_directories") != sorted(EXCLUDED_STATE_DIRS):
        fail(f"snapshot directory exclusion contract differs: {marker}")
    components = data.get("components")
    if not isinstance(components, dict) or set(components) != set(manifest["backup_components"]):
        fail(f"snapshot component set differs: {marker}")
    for component, expected_source in manifest["backup_components"].items():
        detail = components.get(component)
        if not isinstance(detail, dict) or detail.get("source") != expected_source:
            fail(f"snapshot source contract differs for {component}")
        entries = detail.get("entries")
        if not isinstance(entries, list):
            fail(f"snapshot tree manifest is invalid for {component}")
        validate_snapshot_component(root / component, entries)
    return root, data


def restore_state(
    manifest: dict, snapshot: str, component: str, confirm_host: str
) -> None:
    validate_restore_request(manifest, snapshot, component, confirm_host)
    require_root()
    preflight_nas(manifest)
    snapshot_root, metadata = load_snapshot(manifest, snapshot)
    component_detail = metadata["components"][component]
    source = snapshot_root / component
    destination = Path(manifest["backup_components"][component])
    parent = destination.parent
    safe_directory(parent, "state restore parent")
    stage = parent / f".{destination.name}.setup-system-restore-stage"
    old = parent / f".{destination.name}.setup-system-restore-old"
    for path in (stage, old):
        if path.exists() or path.is_symlink():
            fail(f"refusing stale restore transaction path: {path}")
    copy_regular_tree(source, stage)
    validate_snapshot_component(stage, component_detail["entries"])
    had_destination = destination.exists() or destination.is_symlink()
    if had_destination:
        safe_directory(destination, "existing state component")
        os.rename(destination, old)
    try:
        os.rename(stage, destination)
        fsync_dir(parent)
    except BaseException:
        if had_destination and old.exists() and not destination.exists():
            os.rename(old, destination)
        raise
    if had_destination:
        shutil.rmtree(old)
        fsync_dir(parent)
    validate_snapshot_component(destination, component_detail["entries"])
    print(f"Restored {component} state from {snapshot} on {manifest['host']}")


def verify_content(manifest: dict) -> None:
    content = manifest["content"]
    validate_rocknix_content(content["rocknix"])
    quake = content["quake3"]
    validate_quake_content(quake, Path(quake["destination"]))
    morrowind = content["morrowind"]
    validate_morrowind_content(morrowind, Path(morrowind["root"]))
    for name, spec in content["mods"].items():
        validate_mod_source(name, spec)


def verify_quake3(manifest: dict) -> None:
    require_holly(manifest)
    preflight_nas(manifest)
    quake = manifest["content"]["quake3"]
    validate_quake_content(quake, Path(quake["destination"]))
    validate_quake_autoexec(manifest)
    validate_quake_install(manifest)
    print("Quake III NAS content, local controller state, runtime marker, and current link verify")


def status_quake3(manifest: dict) -> None:
    require_holly(manifest)
    quake = manifest["content"]["quake3"]
    checks = [
        ("NAS mount", lambda: preflight_nas(manifest)),
        ("Quake III pak0-pak8", lambda: validate_quake_content(quake, Path(quake["destination"]))),
        ("Quake III controller autoexec", lambda: validate_quake_autoexec(manifest)),
        ("Quake3e runtime", lambda: validate_quake_install(manifest)),
    ]
    failures = 0
    for label, check in checks:
        try:
            check()
        except ContractError as exc:
            failures += 1
            print(f"[FAIL] {label}: {exc}")
        else:
            print(f"[ OK ] {label}")
    if failures:
        fail(f"{failures} Quake III status check(s) failed")


def verify_rocknix(manifest: dict) -> None:
    require_holly(manifest)
    preflight_nas(manifest)
    validate_rocknix_content(manifest["content"]["rocknix"])
    validate_rocknix_state(manifest)
    validate_rocknix_install(manifest)
    print("ROCKNIX NAS ROM root, local state, runtime marker, image, and current link verify")


def status_rocknix(manifest: dict) -> None:
    require_holly(manifest)
    checks = [
        ("NAS mount", lambda: preflight_nas(manifest)),
        ("ROCKNIX ROM root", lambda: validate_rocknix_content(manifest["content"]["rocknix"])),
        ("ROCKNIX state", lambda: validate_rocknix_state(manifest)),
        ("ROCKNIX runtime", lambda: validate_rocknix_install(manifest)),
    ]
    failures = 0
    for label, check in checks:
        try:
            check()
        except ContractError as exc:
            failures += 1
            print(f"[FAIL] {label}: {exc}")
        else:
            print(f"[ OK ] {label}")
    if failures:
        fail(f"{failures} ROCKNIX status check(s) failed")


def verify_openmw(manifest: dict) -> None:
    require_openmw_host(manifest)
    validate_openmw_install(manifest)
    print("OpenMW runtime, authoring tools, desktop assets, marker, and current link verify")


def status_openmw(manifest: dict) -> None:
    require_openmw_host(manifest)
    try:
        validate_openmw_install(manifest)
    except ContractError as exc:
        print(f"[FAIL] OpenMW: {exc}")
        fail("OpenMW status check failed")
    print("[ OK ] OpenMW")


def verify(manifest: dict) -> None:
    require_holly(manifest)
    preflight_nas(manifest)
    verify_content(manifest)
    validate_imported_state(manifest)
    validate_openmw_install(manifest)
    validate_quake_install(manifest)
    validate_rocknix_install(manifest)
    print("All game runtime, content, mutable-state, current-link, and Docker contracts verify")


def status(manifest: dict) -> None:
    require_holly(manifest)
    checks = [
        ("NAS mount", lambda: preflight_nas(manifest)),
        ("content", lambda: verify_content(manifest)),
        ("mutable state", lambda: validate_imported_state(manifest)),
        ("OpenMW", lambda: validate_openmw_install(manifest)),
        ("Quake3e", lambda: validate_quake_install(manifest)),
        ("ROCKNIX", lambda: validate_rocknix_install(manifest)),
    ]
    failures = 0
    for label, check in checks:
        try:
            check()
        except ContractError as exc:
            failures += 1
            print(f"[FAIL] {label}: {exc}")
        else:
            print(f"[ OK ] {label}")
    if failures:
        fail(f"{failures} game-runtime status check(s) failed")


def self_test(manifest: dict) -> None:
    if manifest.get("schema") != 1:
        fail("manifest schema must be 1")
    exact_paths = {
        "host": "holly",
        "cache_root": "/var/cache/setup-system/game-runtimes",
        "install_root": "/opt/games",
        "state_root": "/var/lib/sunshine-host/games",
        "state_cache_root": "/var/cache/sunshine-host/games",
        "snapshot_root": "/usr/local/mnt/iceburg/backup/holly.smeg/game-state",
    }
    for key, expected in exact_paths.items():
        if manifest.get(key) != expected:
            fail(f"manifest {key} must be exactly {expected!r}")
    if manifest.get("openmw_hosts") != ["holly", "rocks"]:
        fail("OpenMW host contract must be exactly ['holly', 'rocks']")
    expected_nas = {
        "alias": "/mnt/iceburg",
        "target": "/mnt/iceburg",
        "source": "donatello.smeg:/iceburg",
        "fstype": "nfs",
    }
    if manifest.get("nas") != expected_nas:
        fail("manifest NAS contract must use the direct /mnt/iceburg mount")
    expected_runtimes = {"openmw", "quake3e", "rocknix"}
    if set(manifest.get("runtimes", {})) != expected_runtimes:
        fail(f"runtime set must be exactly {sorted(expected_runtimes)}")
    for runtime, spec in manifest["runtimes"].items():
        if not HASH_RE.fullmatch(spec["sha256"]):
            fail(f"invalid pinned SHA256 for {runtime}")
        if not re.fullmatch(r"[0-9a-f]{40}|[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{4}", spec["revision"]):
            fail(f"invalid pinned revision for {runtime}")
        marker = runtime_marker(spec, runtime)
        if set(marker) < {"runtime", "version", "revision", "source_sha256", "build_flags"}:
            fail(f"runtime marker contract incomplete for {runtime}")
    pins = {
        "openmw": (
            "0.51.0",
            "7a65e63a5687ff0d51f319ebd529a9e93770fed3cc5408201de4588d1140f144",
            "f4bec41444214a7903bebd178389ca22ca13f646",
        ),
        "quake3e": (
            "2025-10-14-setup-system-1",
            "9ad020f2516774659b0b6c1e595cfc06e8bf9e5247ce002019a94c5784d86d4b",
            "8cd90faf798d94618c871bfb2049d70d4315ad30",
        ),
        "rocknix": (
            "20260718",
            "1f080a6cf2425cd055a7d7de5c6de06394427298e79a3ab875469c9b7971d6ca",
            "25398f713308c384528ac44fcb7a1a876fae90ea",
        ),
    }
    for runtime, (version, digest, revision) in pins.items():
        spec = manifest["runtimes"][runtime]
        if (spec["version"], spec["sha256"], spec["revision"]) != (version, digest, revision):
            fail(f"approved pin differs for {runtime}")
    quake_runtime = manifest["runtimes"]["quake3e"]
    if quake_runtime["url"] != "https://github.com/ec-/Quake3e/archive/refs/tags/2025-10-14.tar.gz":
        fail("Quake3e approved source URL differs")
    if quake_runtime["build_flags"] != "release ARCH=x86_64":
        fail("Quake3e approved build flags differ")
    expected_quake_patch = "patches/quake3e-controller.patch"
    expected_quake_patch_sha256 = "74c5efe8036681625c8c169f1603839024226bc1e1633c8a9cb54e9412d4b746"
    if quake_runtime.get("patch") != expected_quake_patch:
        fail("Quake3e controller patch path differs")
    if quake_runtime.get("patch_sha256") != expected_quake_patch_sha256:
        fail("Quake3e controller patch pin differs")
    quake_patch = Path(__file__).resolve().parent / expected_quake_patch
    safe_regular_file(quake_patch, "pinned Quake3e controller patch")
    if sha256_file(quake_patch) != expected_quake_patch_sha256:
        fail("Quake3e controller patch digest differs")
    if runtime_marker(quake_runtime, "quake3e").get("patch_sha256") != expected_quake_patch_sha256:
        fail("Quake3e runtime marker omits its controller patch")
    rocknix = manifest["runtimes"]["rocknix"]
    expected_rocknix_url = (
        "file:///mnt/iceburg/backup/hal.smeg/wip/games/rocknix/distribution/target/"
        "ROCKNIX-AMD64.x86_64-20260718.tar"
    )
    if rocknix["url"] != expected_rocknix_url:
        fail("ROCKNIX HAL release artifact path differs")
    if rocknix["archive"] != "ROCKNIX-AMD64.x86_64-20260718.tar":
        fail("ROCKNIX release archive name differs")
    if rocknix["archive_root"] != "ROCKNIX-AMD64.x86_64-20260718":
        fail("ROCKNIX release archive root differs")
    if rocknix["docker_image"] != "setup-system/rocknix:20260718":
        fail("ROCKNIX Docker runtime tag differs")
    if rocknix["system_md5"] != "aa403c9beaedd7ce51d891a799eb9cf6":
        fail("ROCKNIX SYSTEM image checksum differs")
    if rocknix["build_flags"] != "unsquashfs -no-progress -d rootfs target/SYSTEM":
        fail("ROCKNIX release extraction contract differs")
    for obsolete_key in ("builder", "patch", "patch_sha256", "rootfs_output"):
        if obsolete_key in rocknix:
            fail(f"ROCKNIX release contract retains obsolete key: {obsolete_key}")
    if "eaadwig" in json.dumps(manifest).lower() or "eadwig" in json.dumps(manifest).lower():
        fail("Eaadwig must remain entirely outside this utility")
    if "portmaster" in json.dumps(manifest).lower():
        fail("PortMaster/OpenMW-on-ROCKNIX is out of scope for this milestone")
    rocknix_content = manifest["content"]["rocknix"]
    if rocknix_content != {"root": "/mnt/iceburg/roms"}:
        fail("ROCKNIX ROM root contract differs")
    quake = manifest["content"]["quake3"]
    if "source" in quake:
        fail("Quake III content must not have a setup-system import source")
    if quake["destination"] != "/mnt/iceburg/roms/ports/quake3/baseq3":
        fail("Quake III canonical NAS destination differs")
    if quake["file_count"] != 9 or quake["bytes"] != 505570007:
        fail("Quake III exact pak count/size contract differs")
    if set(quake["files"]) != {f"pak{index}.pk3" for index in range(9)}:
        fail("Quake III pak0-pak8 filename contract differs")
    if not all(HASH_RE.fullmatch(value) for value in quake["files"].values()):
        fail("Quake III pak hash contract is invalid")
    morrowind = manifest["content"]["morrowind"]
    if morrowind["root"] != "/mnt/iceburg/roms/ports/openmw/Data Files":
        fail("Morrowind data path differs")
    expected_mods = {
        "julan": ("/mnt/iceburg/roms/ports/openmw/lm_plugins/Julan", "."),
        "katisha": ("/mnt/iceburg/roms/ports/openmw/lm_plugins/Katisha", "Data Files"),
    }
    for name, (source, payload) in expected_mods.items():
        spec = manifest["content"]["mods"][name]
        if spec["source"] != source or spec["source_payload"] != payload:
            fail(f"{name} direct source path differs")
        if "destination" in spec:
            fail(f"{name} must be consumed directly without an imported copy")
    state = manifest["state_import"]
    expected_quake_state = "/var/lib/sunshine-host/games/quake3/home/baseq3"
    if state["quake3_baseq3"] != expected_quake_state:
        fail(f"Quake III state path must be exactly {expected_quake_state}")
    expected_components = {"morrowind", "quake3", "rocknix"}
    if set(manifest["backup_components"]) != expected_components:
        fail("backup component contract differs")
    for component, path in manifest["backup_components"].items():
        if not path.startswith(manifest["state_root"] + "/"):
            fail(f"backup component escapes state root: {component}: {path}")
    autoexec = Path(__file__).resolve().parent / manifest["state_import"]["quake3_autoexec_source"]
    expected_autoexec = (
        'seta in_joystick "1"\n'
        'seta in_joystickUseAnalog "1"\n'
        'seta joy_threshold "0.15"\n'
        'bind PAD0_LEFTSTICK_UP "+forward"\n'
        'bind PAD0_LEFTSTICK_DOWN "+back"\n'
        'bind PAD0_LEFTSTICK_LEFT "+moveleft"\n'
        'bind PAD0_LEFTSTICK_RIGHT "+moveright"\n'
        'bind PAD0_RIGHTSTICK_UP "+lookup"\n'
        'bind PAD0_RIGHTSTICK_DOWN "+lookdown"\n'
        'bind PAD0_RIGHTSTICK_LEFT "+left"\n'
        'bind PAD0_RIGHTSTICK_RIGHT "+right"\n'
        'bind PAD0_A "+moveup"\n'
        'bind PAD0_B "+movedown"\n'
        'bind PAD0_X "+button2"\n'
        'bind PAD0_Y "weapnext"\n'
        'bind PAD0_LEFTSHOULDER "weapprev"\n'
        'bind PAD0_RIGHTSHOULDER "weapnext"\n'
        'bind PAD0_LEFTTRIGGER "+speed"\n'
        'bind PAD0_RIGHTTRIGGER "+attack"\n'
        'bind PAD0_BACK "+scores"\n'
        'bind PAD0_LEFTSTICK_CLICK "+speed"\n'
        'bind PAD0_RIGHTSTICK_CLICK "+button2"\n'
        'bind PAD0_DPAD_UP "weapnext"\n'
        'bind PAD0_DPAD_DOWN "weapprev"\n'
        'bind PAD0_DPAD_LEFT "weapon 4"\n'
        'bind PAD0_DPAD_RIGHT "weapon 5"\n'
    )
    if autoexec.read_text(encoding="utf-8") != expected_autoexec:
        fail("repository-managed Quake III controller autoexec differs")
    makefile = (Path(__file__).resolve().parent / "Makefile").read_text(encoding="utf-8")
    required_quake_targets = (
        "build-quake3:",
        "status-quake3:",
        "verify-quake3:",
    )
    for target in required_quake_targets:
        if target not in makefile:
            fail(f"required Quake III Make target is missing: {target}")
    for removed_target in ("import-quake3-content:", "prepare-quake3-state:"):
        if removed_target in makefile:
            fail(f"obsolete Quake III mutation target remains: {removed_target}")
    pane_contracts = ("bash $(PANE) game-runtimes-build-quake3 $(MAKE)",)
    for contract in pane_contracts:
        if contract not in makefile:
            fail(f"Quake III mutating target does not use pane label/argv contract: {contract}")
    required_openmw_targets = (
        "build-openmw:",
        "status-openmw:",
        "verify-openmw:",
    )
    for target in required_openmw_targets:
        if target not in makefile:
            fail(f"required OpenMW Make target is missing: {target}")
    openmw_pane_contract = "bash $(PANE) game-runtimes-build-openmw $(MAKE)"
    if openmw_pane_contract not in makefile:
        fail("OpenMW mutating target does not use its pane label/argv contract")
    required_rocknix_targets = (
        "build-rocknix:",
        "clean-rocknix-cache:",
        "status-rocknix:",
        "verify-rocknix:",
    )
    for target in required_rocknix_targets:
        if target not in makefile:
            fail(f"required ROCKNIX Make target is missing: {target}")
    rocknix_pane_contract = "bash $(PANE) game-runtimes-build-rocknix $(MAKE)"
    if rocknix_pane_contract not in makefile:
        fail("ROCKNIX mutating target does not use its pane label/argv contract")
    rocknix_clean_pane_contract = "bash $(PANE) game-runtimes-clean-rocknix-cache $(MAKE)"
    if rocknix_clean_pane_contract not in makefile:
        fail("ROCKNIX cache cleanup target does not use its pane label/argv contract")
    print("game_runtimes manifest, pin, path, marker, and backup contracts are valid")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--manifest", type=Path, required=True)
    subparsers = result.add_subparsers(dest="command", required=True)
    for name in (
        "self-test",
        "status",
        "verify",
        "status-openmw",
        "verify-openmw",
        "status-quake3",
        "verify-quake3",
        "status-rocknix",
        "verify-rocknix",
        "import-state",
        "build-openmw",
        "build-quake3",
        "build-rocknix",
        "clean-rocknix-cache",
        "build-all",
        "backup-state",
    ):
        subparsers.add_parser(name)
    for name in ("validate-restore", "restore-state"):
        restore = subparsers.add_parser(name)
        restore.add_argument("--snapshot", required=True)
        restore.add_argument("--component", required=True)
        restore.add_argument("--confirm-host", required=True)
    return result


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        manifest = load_manifest(arguments.manifest)
        commands = {
            "self-test": self_test,
            "status": status,
            "verify": verify,
            "status-openmw": status_openmw,
            "verify-openmw": verify_openmw,
            "status-quake3": status_quake3,
            "verify-quake3": verify_quake3,
            "status-rocknix": status_rocknix,
            "verify-rocknix": verify_rocknix,
            "import-state": import_state,
            "build-openmw": build_openmw,
            "build-quake3": build_quake3,
            "build-rocknix": build_rocknix,
            "clean-rocknix-cache": clean_rocknix_cache,
            "build-all": build_all,
            "backup-state": backup_state,
        }
        if arguments.command in commands:
            commands[arguments.command](manifest)
        elif arguments.command == "validate-restore":
            validate_restore_request(
                manifest, arguments.snapshot, arguments.component, arguments.confirm_host
            )
            print("restore request is explicit and valid")
        elif arguments.command == "restore-state":
            restore_state(
                manifest, arguments.snapshot, arguments.component, arguments.confirm_host
            )
        else:
            fail(f"unsupported command: {arguments.command}")
    except ContractError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
