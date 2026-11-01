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
  diffusion_models/ernie-image.safetensors
  text_encoders/ministral-3-3b.safetensors
  vae/flux2-vae.safetensors
```

The role also creates `/opt/models/loras` and registers `loras: loras/` in
`/etc/comfyui/extra_model_paths.yaml`. ComfyUI discovers supported LoRA files
recursively there. Locally trained adapters are published separately from the
three pinned downloads, so `make clean` does not remove them. The sibling
`lora-char` repository's `make publish-comfyui` publishes its completed adapter
and verifies discovery through the ComfyUI API.

The role's `comfyui-model-paths` tag applies just platform/manifest checks,
model/state directories, search paths and service activation. It uses the
existing hostname-checked `test_role` runner and leaves runtime, package and
driver provisioning out of a LoRA publication.

To replace the model artifacts, update their URLs, sizes and SHA-256 hashes in
`models.json`, then run:

```sh
make clean
make
```

`clean` deletes only the three explicitly listed ERNIE-Image weights and their
partial downloads, leaving unrelated models, uploads and generated output
untouched. During setup, the checksum-verified previous VAE is preserved as
`vae/flux2-vae-klein.safetensors`; the previous Klein diffusion model and text
encoder are also left in place for switching back.
Deleted weights can be downloaded again. Stop generation before replacing
weights; reapply the role afterwards to publish the new inventory and restart
the service. If a filename changes, clean with the old manifest before editing
it, and update the workflow loader filename as well.

The ERNIE-Image files are pinned to an immutable revision of
`Comfy-Org/ERNIE-Image` and verified by size and SHA-256 before installation.

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

The same lock includes `rocm[devel]==7.14.1`. Setup and `make prepare` initialize
its development tree under the environment's `site-packages/_rocm_sdk_devel`,
providing the HIP compiler, headers and HIP/hipBLAS/rocBLAS CMake packages for
external builds such as the Philby models pane's llama.cpp. Setup owns this SDK;
consuming workspaces own their source, builds and runtime configuration. Keep
the SDK in place while those binaries depend on its libraries.

`rocm-sdk init` and `rocm-sdk path` can expand files and update package records;
run initialization through setup, not from a consuming workspace. Read-only
inspection can locate the initialized `_rocm_sdk_devel` package and check its
files directly. No separate global ROCm APT repository is used for this SDK.

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

The ERNIE-Image native API graph is in `workflows/text-to-image-api.json`. The
previous Klein reference-editing graph is retained for switching back.

The managed ERNIE graph loads `antigone/antigone-ernie-step500.safetensors`
through node 14 (`LoraLoaderModelOnly`) at strength 1.0 by default. Both its
scheduler and guider use that adapted model. Include `antigone` in the prompt
to request the character; change node 14's `strength_model` to adjust the
effect (0 disables it). The adapter must first be published from `lora-char`.
Existing custom workflows are unaffected; clients holding an older copy of
the managed graph need to reload `/etc/comfyui/text-to-image-api.json`.

Their inputs are:

| Parameter | Node input |
| --- | --- |
| Prompt | `4.inputs.text` |
| Seed | `6.inputs.noise_seed` |
| ERNIE LoRA strength | `14.inputs.strength_model` |
| ERNIE output width/height | `5.inputs.width/height` |
| Klein edit output width/height | `5.inputs.width/height` and `8.inputs.width/height` |
| Reference image | `14.inputs.image` in the editing graph |

Use dimensions divisible by 16. Upload a reference with `/upload/image`, then
put its returned filename (including any subfolder) in node 14. Reference
conditioning preserves the image's aspect ratio and limits it to roughly one
megapixel; output dimensions are independently exposed. The ERNIE-Image
workflow uses the standard BF16 8B model, batch size one, Euler sampling, the
simple scheduler, 50 steps, CFG 4, denoise 1, a fixed seed of 42, and 1376 x 768
landscape output. ComfyUI's automatic memory management remains enabled.

Post `{"prompt": <API graph>, "client_id": "<uuid>"}` to `/prompt`; listen on
`/ws`, obtain the output descriptors from `/history/<prompt_id>`, and download
them through `/view`. The helper client implements the complete sequence:

```sh
/opt/comfyui/venv/bin/python client.py generate --workflow text-to-image \
  --prompt 'A cinematic landscape scene at golden hour' --seed 42 \
  --width 1376 --height 768 --output .runtime/example

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
