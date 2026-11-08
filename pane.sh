#!/usr/bin/env bash
set -euo pipefail

if (( $# < 2 )); then
    echo "usage: bash pane.sh <name> <command...>" >&2
    exit 2
fi
: "${TMUX:?Run this target inside tmux}"
: "${TMUX_PANE:?Current tmux pane is required}"

name=$1
shift
socket=${TMUX%%,*}
session=$(tmux -S "$socket" display-message -p -t "$TMUX_PANE" '#{session_id}:')
pane=$(tmux -S "$socket" split-window -v -t "$session" -c "$PWD" -P -F '#{pane_id}' \
    bash -c '
        set -euo pipefail
        tmux set-option -p -t "$TMUX_PANE" remain-on-exit on
        tmux select-pane -t "$TMUX_PANE" -T "$1"
        shift
        exec "$@"
    ' bash "$name" "$@")
printf 'Started pane %s (%s)\n' "$pane" "$name"
