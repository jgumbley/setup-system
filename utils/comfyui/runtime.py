"""Prepare and inspect the native ComfyUI environment, invoked only through make."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def prepare(role, root, uv):
    pins = json.loads((role / "files/runtime.json").read_text())
    root.mkdir(parents=True, exist_ok=True)
    run(uv, "python", "install", pins["python"])
    if not (root / "venv/bin/python").exists():
        run(uv, "venv", "--python", pins["python"], str(root / "venv"))
    run(uv, "pip", "sync", "--python", str(root / "venv/bin/python"),
        "--require-hashes", "--index-strategy", "unsafe-best-match",
        str(role / "files/requirements.lock"))
    run(str(root / "venv/bin/python"), "-B", "-m", "rocm_sdk", "init")
    app = root / "app"
    if not app.exists():
        run("git", "clone", "--branch", pins["comfyui_tag"], "--depth", "1", pins["comfyui_repo"], str(app))
    actual = subprocess.check_output(["git", "-C", str(app), "rev-parse", "HEAD"], text=True).strip()
    if actual != pins["comfyui_commit"]:
        raise RuntimeError(f"ComfyUI revision mismatch: {actual}")
    run(uv, "pip", "check", "--python", str(root / "venv/bin/python"))


def versions(root):
    import torch
    data = {
        "python": platform.python_version(), "kernel": platform.release(),
        "os": platform.freedesktop_os_release()["PRETTY_NAME"],
        "loaded_amdgpu_srcversion": Path("/sys/module/amdgpu/srcversion").read_text().strip(),
        "installed_amdgpu_srcversion": subprocess.check_output(
            ["modinfo", "-F", "srcversion", "amdgpu"], text=True).strip(),
        "driver_packages": subprocess.check_output(
            ["dpkg-query", "-W", "amdgpu-dkms", "amdgpu-dkms-firmware"], text=True).strip(),
        "torch": torch.__version__, "hip": torch.version.hip,
        "gpu_available": torch.cuda.is_available(),
        "comfyui_commit": subprocess.check_output(
            ["git", "-c", f"safe.directory={root / 'app'}", "-C", str(root / "app"), "rev-parse", "HEAD"],
            text=True).strip(),
        "packages": dict(sorted((d.metadata["Name"], d.version) for d in importlib.metadata.distributions())),
    }
    if torch.cuda.is_available():
        data["gpu"] = torch.cuda.get_device_name(0)
        data["vram_bytes"] = torch.cuda.get_device_properties(0).total_memory
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "versions"])
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--role", type=Path)
    parser.add_argument("--uv")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.role, args.root, args.uv)
    else:
        versions(args.root)
