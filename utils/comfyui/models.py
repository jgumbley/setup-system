"""Manage only the model files explicitly named in models.json."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


def entries(manifest):
    data = json.loads(Path(manifest).read_text())
    root = Path(data["root"])
    if root != Path("/opt/models"):
        raise ValueError("The model manifest must use /opt/models")
    result = []
    for item in data["models"]:
        relative = Path(item["path"])
        if (relative.is_absolute() or ".." in relative.parts
                or len(relative.parts) != 2 or relative.suffix != ".safetensors"
                or relative.parts[0] not in {"diffusion_models", "text_encoders", "vae"}):
            raise ValueError(f"Invalid managed model path: {relative}")
        if len(item["sha256"]) != 64 or any(c not in "0123456789abcdef" for c in item["sha256"]):
            raise ValueError("Invalid SHA-256")
        if item["size"] <= 0 or not item["url"].startswith("https://huggingface.co/"):
            raise ValueError("Invalid model size or URL")
        target = root / relative
        if target.resolve() != target or target.with_suffix(target.suffix + ".part").is_symlink():
            raise ValueError(f"Refusing symlinked model path: {target}")
        result.append((target, item))
    if len({path for path, _ in result}) != len(result):
        raise ValueError("Duplicate model path")
    return root, result


def valid(path, item):
    if not path.is_file() or path.stat().st_size != item["size"]:
        return False
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest() == item["sha256"]


def download(target, item):
    if target.exists():
        if not valid(target, item):
            raise RuntimeError(f"Checksum mismatch: {target}; run make clean before replacing weights")
        print(f"Verified existing {target}", flush=True)
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + ".part")
    remaining = max(0, item["size"] - (partial.stat().st_size if partial.exists() else 0))
    if shutil.disk_usage(target.parent).free < remaining + 1024**3:
        raise RuntimeError(f"Insufficient disk space for {target}")
    if not valid(partial, item):
        if partial.exists() and partial.stat().st_size >= item["size"]:
            raise RuntimeError(f"Invalid complete partial file: {partial}; run make clean")
        subprocess.run([
            "curl", "--fail", "--location", "--proto", "=https", "--proto-redir", "=https",
            "--retry", "5", "--retry-delay", "3", "--connect-timeout", "30",
            "--continue-at", "-", "--output", str(partial), item["url"],
        ], check=True)
    if not valid(partial, item):
        raise RuntimeError(f"Downloaded file failed size/SHA-256 verification: {partial}")
    partial.chmod(0o644)
    os.replace(partial, target)
    print(f"Installed {target}", flush=True)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["download", "verify", "clean"])
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()
    root, models = entries(args.manifest)
    if not root.is_dir():
        raise RuntimeError("Missing /opt/models; apply the comfyui Ansible role first")
    # Shared with all utility invocations, including those launched by Ansible.
    with (root / ".comfyui-models.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        changed = False
        for target, item in models:
            if args.action == "download":
                changed = download(target, item) or changed
            elif args.action == "verify":
                if not valid(target, item):
                    raise RuntimeError(f"Missing or invalid model: {target}")
                print(f"Verified {target}", flush=True)
            else:
                for path in (target, target.with_suffix(target.suffix + ".part")):
                    if path.exists():
                        path.unlink()
                        print(f"Removed {path} (recoverable by make)", flush=True)
                        changed = True
        print(f"changed={str(changed).lower()}")


if __name__ == "__main__":
    main()
