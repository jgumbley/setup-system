# Holly's native ComfyUI

The `comfyui` Ansible role in `setup-system` owns Holly's native Python runtime,
AMDGPU driver, configuration and systemd service. Apply it through `make setup`.
For development, `make test_role role=comfyui` uses the same exact-host role
selection. The helper `make -C utils/comfyui setup-pane` opens that operation in
the `comfyui-setup` tmux session, with the `comfyui` tag to skip unrelated roles.

## Models

From this directory:

```sh
make
make verify
```

Ansible creates `/opt/models` with the correct ownership, then calls the same
`make models` target as the service user. `models.json` is the single source for
the destination paths, immutable Hugging Face revision URLs, file sizes and
SHA-256 hashes. All three files are public downloads; no Hugging Face token is
required. Downloads resume into `.part` files and become visible to ComfyUI only
after size and hash verification. A lock prevents concurrent download/clean
operations. Existing files are verified on every invocation, including Ansible
reruns; incorrect files cause an explicit failure.

Files managed by this utility:

```text
/opt/models/
  diffusion_models/flux-2-klein-4b.safetensors
  text_encoders/qwen_3_4b.safetensors
  vae/flux2-vae.safetensors
```

To replace the model artifacts, update their URLs, sizes and SHA-256 hashes in
`models.json`, then run:

```sh
make clean
make
```

`clean` deletes only the three explicitly listed weights and their partial
downloads, leaving unrelated models, uploads and generated output untouched.
Deleted weights can be downloaded again. Stop generation before replacing
weights; reapply the role afterwards to publish the new inventory and restart
the service. If a filename changes, clean with the old manifest before editing
it, and update the workflow loader filename as well.

The Hal backup supplied the deployment pattern and older workflow examples.
Its FLUX.2 VAE has SHA-256
`d64f3a68e1cc4f9f4e29b6e0da38a0204fe9a49f2d4053f0ec1fa1ca02f9c4b5`,
which differs from the requested Klein VAE. None of the archived model bytes
are reused in this installation.

## Runtime and driver

`../../roles/comfyui/files/runtime.json` records the selected versions.
`requirements.in` pins the upstream ComfyUI requirements by commit and selects
AMD's `gfx1100` PyTorch wheels. `requirements.lock` fixes every transitive Python
dependency and its accepted artifact hashes. After changing runtime versions,
regenerate it using `make lock`, validate with `make prepare` and
`make gpu-check`, then apply the role. Keep the Python/Torch fields in
`runtime.json` synchronized with `requirements.in`.

The initial selection is ComfyUI v0.34.0, Python 3.12.13, ROCm 7.14.1,
PyTorch 2.11.0, torchvision 0.26.0 and torchaudio 2.11.0. The runtime is under
`/opt/comfyui`; mutable state is under `/var/lib/comfyui` and caches under
`/var/cache/comfyui`.

AMD's available Ubuntu Resolute driver repository is pinned to 31.40.1 with its
matching firmware. On 2026-09-05 the newer documented 31.50.0 repository URL
returned HTTP 404. Installing the DKMS driver prepares the next boot; the role
does not reboot or unload Holly's active display driver. After reboot, verify
the loaded module and rerun the benchmark before calling that driver validated.

Sources:

- [ROCm 7.14.1 compatibility matrix](https://rocm.docs.amd.com/en/docs-7.14.1/compatibility/compatibility-matrix.html)
- [AMD native PyTorch installation](https://rocm.docs.amd.com/projects/ai-ecosystem/en/latest/frameworks/pytorch/install.html)
- [AMD 31.40.1 Ubuntu driver installation](https://instinct.docs.amd.com/projects/amdgpu-docs/en/docs-31.40.1/install/detailed-install/package-manager/package-manager-ubuntu.html)
- [Native Klein workflows](https://docs.comfy.org/tutorials/flux/flux-2-klein)

## Connection

On Holly, use `http://127.0.0.1:8188`. For a remote client, open an SSH tunnel:

```sh
ssh -N -L 8188:127.0.0.1:8188 system@holly.smeg
```

Then use `http://127.0.0.1:8188` on that client as well. Authentication is the
existing SSH key authentication to Holly. The listener is loopback-only.
WebSockets use `ws://127.0.0.1:8188/ws?clientId=<your-uuid>` through the same
tunnel. The standard `/upload/image`, `/prompt`, `/history`, `/view`, `/queue`,
`/object_info`, `/models/*` and `/ws` routes are provided directly by ComfyUI.
`--disable-api-nodes` disables external paid-provider nodes; it does not disable
these local automation routes.

In Blender's ComfyUI add-on preferences, set Server Address to that HTTP URL.
No provider API key or custom authentication headers are required. Import one
of the API workflows below. These use core nodes only. Generated PNGs contain
the submitted `prompt` graph; the included client also supplies the editable
UI `workflow` metadata and checks both when retrieving each PNG.

## Workflows and automation

Exported native API graphs are in `workflows/text-to-image-api.json` and
`workflows/reference-edit-api.json`. Their inputs are:

| Parameter | Node input |
| --- | --- |
| Prompt | `4.inputs.text` |
| Seed | `6.inputs.noise_seed` |
| Output width/height | `5.inputs.width/height` and `8.inputs.width/height` |
| Reference image | `14.inputs.image` in the editing graph |

Use dimensions divisible by 16. Upload a reference with `/upload/image`, then
put its returned filename (including any subfolder) in node 14. Reference
conditioning preserves the image's aspect ratio and limits it to roughly one
megapixel; output dimensions are independently exposed. Both workflows use
the full BF16 distilled model, batch size one, Euler sampling, CFG 1, four steps,
and ComfyUI's default memory management.

Post `{"prompt": <API graph>, "client_id": "<uuid>"}` to `/prompt`; listen on
`/ws`, obtain the output descriptors from `/history/<prompt_id>`, and download
them through `/view`. The helper client implements the complete sequence:

```sh
/opt/comfyui/venv/bin/python client.py generate --workflow text-to-image \
  --prompt 'An evenly lit weathered limestone material study' --seed 42 \
  --width 1024 --height 1024 --output .runtime/example

/opt/comfyui/venv/bin/python client.py generate --workflow reference-edit \
  --image reference.png --prompt 'Change the stone to red sandstone' \
  --seed 43 --width 1024 --height 1024 --output .runtime/edit
```

The initial workflows produce texture source images. Seamless tiling and
physically calibrated normal/roughness maps are not guaranteed by these graphs.

## Verification and performance

```sh
make test
make status
make versions
make benchmark
```

For an agent-run benchmark, `make benchmark-pane` uses the existing
`comfyui-setup` tmux session; `make benchmark-status` reads its progress.
`make inspect` reports the loaded and installed driver, resources and listener.

The benchmark runs the two workflows three times each with different seeds,
uploads a generated material as the edit reference, checks PNG dimensions and
metadata, and writes outputs, histories, API/UI workflows, and `benchmark.json`
under `.runtime/results/<timestamp>/`. It checks for an idle queue before each
request. Time is measured from submission through the WebSocket completion
event, including model loading and image saving. VRAM is sampled every 20 ms
from amdgpu's whole-device counter; the report includes the baseline, sampled
peak, and increase above baseline. It is not a per-process PyTorch allocation
peak, and includes Holly's desktop or any other GPU workload.

Each invocation chooses a new seed from the current Unix time, so reruns do not
reuse fully cached outputs. Set `BENCHMARK_SEED=<integer>` to reproduce a run;
repeating the same seed on a warm server can reuse cached outputs. PNG validation
allows ComfyUI's added `is_changed` image fingerprint while checking the rest of
the submitted graph and the complete editable workflow metadata.

Use an idle GPU for comparable performance results. The first text-to-image
run is cold only when the service has just started. Reference editing follows
text-to-image and therefore starts with some runtime/model state already warm.
`make prepare` and `make dev-server` are developer checks using ignored
workspace state; the latter listens on port 8189 and is not the persistent
service.

### Validation on 2026-09-05

The enabled persistent service passed six generations at 1024 × 1024, batch one,
four steps, using the full BF16 Klein weights and normal memory management.
All three model SHA-256 checks and all five utility tests passed. Upload, prompt,
history, image retrieval and WebSocket completion were exercised successfully;
all six returned PNGs passed dimensions and API/UI workflow metadata checks.

| Workflow | First run in complete benchmark | Warm median | Highest sampled whole-GPU VRAM |
| --- | --- | --- | --- |
| Text-to-image | 3.359 s | 2.218 s | 23.714 GiB |
| Reference editing | 5.692 s | 4.439 s | 23.621 GiB |

This complete benchmark started with a warm service. The preceding first
text-to-image request after service startup took 5.891 s and peaked at
23.791 GiB. That earlier benchmark stopped at an overly strict metadata check
on reference editing; the client was corrected before the complete run above.
These are sampled whole-device readings, not a minimum VRAM requirement.

Local artifacts:

- [Complete benchmark](.runtime/results/20260905T142048Z/benchmark.json)
- [Generated limestone](.runtime/results/20260905T142048Z/text-to-image-first-0.png)
- [Reference-guided stone edit](.runtime/results/20260905T142048Z/reference-edit-first-0.png)
- [Exact installed versions](.runtime/installed-versions.json)

The images are usable material studies, but include borders and are not seamless
textures. The edit broadly preserves the block layout with some changed joints.

The host has Ubuntu 26.04, kernel `7.0.0-29-generic`, 61 GiB system RAM and
3.3 TiB available disk. The loaded AMDGPU source version is
`3C579E7F273939F4A3F71D3`; the installed DKMS source version is
`88983A47E73AF492726AD7C`. **The new driver still requires a reboot and another
benchmark.** These measurements validate the currently loaded driver only.
