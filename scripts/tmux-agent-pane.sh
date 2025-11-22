#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "Usage: tmux-agent-pane.sh <pane-label> <command ...>" >&2
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

When the command finishes you can close this pane (Ctrl-b x) or leave it open, and
the main terminal/agent can read progress via tmux capture-pane.

EOF

status=0
if "$@"; then
  status=0
else
  status=$?
fi

cat <<EOF

[agent:${pane_label}] Command exited with status ${status}.
Pane will stay open for review. Press ENTER (in this pane) whenever you are ready
to close it, or hit Ctrl-b x to kill the pane manually.

EOF

if [ -t 0 ]; then
  # shellcheck disable=SC2034
  read -r _ || true
else
  while :; do sleep 3600; done
fi

exit "$status"
