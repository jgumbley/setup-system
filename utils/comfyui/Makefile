.DEFAULT_GOAL := models
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
UTILITY := $(abspath .)
ROLE := $(abspath ../../roles/comfyui)
UV := $(shell command -v uv)
BENCHMARK_SEED ?= $(shell date +%s)
export UV_CACHE_DIR := $(UTILITY)/.runtime/uv-cache
export UV_PYTHON_INSTALL_DIR := $(UTILITY)/.runtime/python
export PYTHONDONTWRITEBYTECODE := 1
export XDG_CACHE_HOME := $(UTILITY)/.runtime/cache
export HF_HOME := $(UTILITY)/.runtime/cache/huggingface
export TORCH_HOME := $(UTILITY)/.runtime/cache/torch

.PHONY: models clean verify help lock prepare gpu-check test setup-pane status benchmark benchmark-pane benchmark-status inspect versions dev-server

help:
	@printf '%s\n' 'make                   Download and verify the pinned models to /opt/models' 'make verify            Verify all model hashes' 'make clean             Remove only the three managed models and partial downloads' 'make lock              Resolve and hash-lock the Python dependencies' 'make prepare           Prepare a workspace runtime for native GPU validation' 'make gpu-check         Test native ROCm, BF16, attention and convolution' 'make test              Run utility tests and workflow validation' 'make setup-pane        Apply the Holly role in a sudo-capable tmux pane' 'make status            Show the persistent service' 'make benchmark         Exercise both API workflows and record timing/VRAM' 'make versions          Report installed runtime versions'

# Python owns the file checks so a changed manifest cannot leave an old weight
# silently accepted by make's timestamp checks. Ansible calls this same target.
models:
	python3 -B models.py download --manifest models.json

verify:
	python3 -B models.py verify --manifest models.json

clean:
	python3 -B models.py clean --manifest models.json

lock:
	$(UV) pip compile $(ROLE)/files/requirements.in --python-version 3.12 --index-strategy unsafe-best-match --generate-hashes --emit-index-url --output-file $(ROLE)/files/requirements.lock --quiet

prepare:
	python3 -B runtime.py prepare --role $(ROLE) --root $(UTILITY)/.runtime --uv $(UV)

gpu-check:
	.runtime/venv/bin/python -B gpu_check.py

dev-server:
	@mkdir -p .runtime/state/user .runtime/state/input .runtime/state/output .runtime/state/temp
	.runtime/venv/bin/python .runtime/app/main.py --listen 127.0.0.1 --port 8189 --base-directory $(UTILITY)/.runtime/state --disable-auto-launch --disable-all-custom-nodes --disable-api-nodes

test:
	@mkdir -p .runtime
	python3 -B -m unittest discover -s tests -v

setup-pane:
	@tmux has-session -t comfyui-setup 2>/dev/null || tmux new-session -d -s comfyui-setup -x 160 -y 48 -c $(abspath ../..)
	@ANSIBLE_RUN_TAGS=comfyui TMUX="$$(tmux display-message -p -t comfyui-setup '#{socket_path},#{pid},0')" TMUX_PANE="$$(tmux display-message -p -t comfyui-setup '#{pane_id}')" $(MAKE) -C ../.. test_role role=comfyui

status:
	systemctl --no-pager --full status comfyui.service

benchmark:
	/opt/comfyui/venv/bin/python -B client.py benchmark --seed $(BENCHMARK_SEED) --output $(UTILITY)/.runtime/results

benchmark-pane:
	@tmux has-session -t comfyui-setup
	@TMUX="$$(tmux display-message -p -t comfyui-setup '#{socket_path},#{pid},0')" TMUX_PANE="$$(tmux display-message -p -t comfyui-setup '#{pane_id}')" bash ../../pane.sh comfyui-benchmark $(MAKE) benchmark

benchmark-status:
	@tmux list-panes -s -t comfyui-setup -F '#{pane_id} #{pane_title}' | while read -r pane title; do if [ "$$title" = comfyui-benchmark ]; then tmux capture-pane -p -t "$$pane" -S -40; fi; done

inspect:
	uname -r
	cat /sys/module/amdgpu/srcversion
	modinfo -F srcversion amdgpu
	modinfo -F filename amdgpu
	dpkg-query -W amdgpu-dkms amdgpu-dkms-firmware
	dkms status
	free -h
	df -h /opt/models
	ss -ltn '( sport = :8188 )'
	journalctl -u comfyui.service -n 35 --no-pager
	tmux list-panes -s -t comfyui-setup -F '#{pane_id} #{pane_title}'

versions:
	/opt/comfyui/venv/bin/python -B runtime.py versions --root /opt/comfyui

.PHONY: capture-ernie-repro reproduce-ernie setup-status
capture-ernie-repro:
	@mkdir -p .runtime/ernie-repro
	@test ! -e .runtime/ernie-repro/original-history.json && test ! -e .runtime/ernie-repro/original.png || { echo "Original reproduction already captured; refusing to overwrite it" >&2; exit 2; }
	curl -fsS http://127.0.0.1:8188/history/d407cee8-d5ac-4222-b933-ccd189f298a3 -o .runtime/ernie-repro/original-history.json
	curl -fsS 'http://127.0.0.1:8188/view?filename=buildwas-r0060_00001_.png&subfolder=worldbuilding&type=output' -o .runtime/ernie-repro/original.png

reproduce-ernie:
	@test -n "$(CASE)" || { echo "usage: make reproduce-ernie CASE=<diagnostic-case>" >&2; exit 2; }
	/opt/comfyui/venv/bin/python -B client.py reproduce-ernie --history .runtime/ernie-repro/original-history.json --output .runtime/ernie-repro/$(CASE)

setup-status:
	@tmux capture-pane -pt $(PANE) -S -65
