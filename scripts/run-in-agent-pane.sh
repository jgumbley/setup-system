#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 2 ]; then
  cat >&2 <<'EOF'
Usage: run-in-agent-pane.sh <pane-label> <command ...>
Creates a tmux pane above the current one and runs the given command there.
EOF
  exit 1
fi

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux is required to start an agent pane." >&2
  exit 1
fi

if [ -z "${TMUX:-}" ]; then
  echo "run-in-agent-pane.sh must be executed from inside an existing tmux session." >&2
  exit 1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
pane_label="$1"
shift
pane_height="${AGENT_PANE_PERCENT:-45}"
runner="$repo_root/scripts/tmux-agent-pane.sh"

if [ ! -f "$runner" ]; then
  echo "Missing helper $runner" >&2
  exit 1
fi

cmd_display="$(printf ' %q' "$@")"
cmd_display="${cmd_display:1}"

pane_id="$(
  tmux split-window -b -v -p "$pane_height" -c "$repo_root" -PF '#{pane_id}' \
    bash "$runner" "$pane_label" "$@"
)"

cat <<EOF
Started tmux pane "$pane_id" for "$pane_label".
Command: $cmd_display
Watch the pane above for prompts. Type any sudo/BECOME passwords there, not here.
To capture its output later: tmux capture-pane -pt $pane_id
The pane will stay open after the command exits; press Enter in that pane (or
kill it) once you are done reviewing the logs.
EOF
