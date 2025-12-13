.PHONY: digest ingest clean agent-%

CLIPBOARD_CMD := pbcopy
ifeq ($(shell uname -s),Linux)
CLIPBOARD_CMD := wl-copy
endif

define success
	@printf '\033[32m\n'; \
	set -- 🦴 💉 🐶 😺 💊; \
	icon_idx=$$(( $$(od -An -N2 -tu2 /dev/urandom | tr -d ' ') % $$# + 1 )); \
	while [ $$icon_idx -gt 1 ]; do shift; icon_idx=$$((icon_idx - 1)); done; \
	icon=$$1; \
	parent_info=$$(ps -o ppid= -p $$$$ 2>/dev/null | tr -d ' '); \
	[ -n "$$parent_info" ] || parent_info="n/a"; \
	printf "%s > \033[33m%s\033[0m accomplished\n" "$$icon" "$(@)"; \
	printf "\033[90m{{{ %s | user=%s | host=%s | procid=%s | parentproc=%s }}}\033[0m\n\033[0m" "$$(date +%Y-%m-%d_%H:%M:%S)" "$$(whoami)" "$$(hostname)" "$$$$" "$$parent_info"
endef

.venv/: requirements.txt
	uv venv .venv/
	uv pip install -r requirements.txt
	$(call success)

digest:
	@echo "=== Project Digest ==="
	@for file in $$(find . -path "./.uv-cache" -prune -o -type f \( -name "*.py" -o -name "*.md" -o -name "*.txt" -o -name "Makefile" \) -print | grep -v venv | grep -v __pycache__ | sort); do \
		echo ""; \
		echo "--- $$file ---"; \
		cat "$$file"; \
	done
	$(call success)

ingest:
	$(MAKE) digest | $(CLIPBOARD_CMD)
	$(call success)

clean:
	rm -Rf .venv/
	$(call success)

# Run any make target inside a tmux agent pane so a human can type secrets
# locally while the agent watches output. Usage: make agent-<target>
agent-%:
	@cmd_target="$*"; \
	if [ -z "$$cmd_target" ]; then \
		echo "Usage: make agent-<target>"; exit 1; \
	fi; \
	if ! command -v tmux >/dev/null 2>&1; then \
		echo "tmux is required to start an agent pane." >&2; exit 1; \
	fi; \
	if [ -z "$$TMUX" ]; then \
		echo "agent panes must be started from inside an existing tmux session." >&2; exit 1; \
	fi; \
	repo_root="$(PWD)"; \
	label="agent-$$cmd_target"; \
	pane_height="${AGENT_PANE_PERCENT:-45}"; \
	current_height="$$(tmux display-message -p '#{pane_height}' 2>/dev/null || true)"; \
	pane_lines="$$pane_height"; \
	if [ -n "$$current_height" ] && [ "$$current_height" -gt 0 ] 2>/dev/null; then \
		pane_lines=$$(( current_height * pane_height / 100 )); \
		[ "$$pane_lines" -lt 3 ] && pane_lines=3; \
	fi; \
	runner_script="$$(mktemp)"; \
	cat > "$$runner_script" <<'RUNNER_EOF'; \
#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "Usage: tmux-agent-pane <pane-label> <command ...>" >&2
  exit 1
fi

pane_label="$1"
shift

cmd_display="$(printf ' %q' "$@")"
cmd_display="${cmd_display:1}"

# Set the pane title so it is easy to spot visually.
printf '\033]2;%s\007' "$pane_label"

cat <<EOF
[agent:${pane_label}] Running ${cmd_display}

If you are prompted for sudo/BECOME credentials, type them directly in this pane.
Secrets typed here are not echoed, so they will not appear in captured output.

When the command finishes you can press Enter in this pane to rerun it, or close
the pane (Ctrl-b x) to stop. The main terminal/agent can read progress via tmux
capture-pane.

EOF

status=0
while :; do
  if "$@"; then
    status=0
  else
    status=$?
  fi

  cat <<EOF

[agent:${pane_label}] Command exited with status ${status}.
Press Enter in this pane to run it again, or close the pane (Ctrl-b x) to stop.

EOF

  if [ ! -t 0 ]; then
    break
  fi
  # Wait for Enter (not echoed)
  # shellcheck disable=SC2034
  read -r _ || break
done

exit "$status"
RUNNER_EOF
	pane_id="$$(tmux split-window -b -v -l "$$pane_lines" -c "$$repo_root" -P -F '#{pane_id}' \
		bash "$$runner_script" "$$label" $(MAKE) $$cmd_target)"; \
	rm -f "$$runner_script"; \
	cat <<EOF
Started tmux pane "$$pane_id" for "$$label".
Command: make $$cmd_target
Watch the pane above for prompts. Type any sudo/BECOME passwords there, not here.
To capture its output later: tmux capture-pane -pt $$pane_id
The pane will stay open after each run; press Enter in that pane to rerun, or close it to stop.
EOF
