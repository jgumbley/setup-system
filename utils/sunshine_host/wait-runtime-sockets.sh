#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 2 ]; then
  printf 'usage: %s TIMEOUT_SECONDS SOCKET [SOCKET ...]\n' "$0" >&2
  exit 2
fi

timeout_seconds="$1"
shift
case "$timeout_seconds" in
  *[!0-9]*|'')
    printf 'timeout must be a non-negative integer: %s\n' "$timeout_seconds" >&2
    exit 2
    ;;
esac

deadline=$((SECONDS + timeout_seconds))
while :; do
  missing=
  for socket_path in "$@"; do
    if [ ! -S "$socket_path" ]; then
      missing="$socket_path"
      break
    fi
  done
  [ -z "$missing" ] && exit 0
  [ "$SECONDS" -lt "$deadline" ] || break
  sleep 0.1
done

printf 'timed out waiting for runtime socket(s):\n' >&2
for socket_path in "$@"; do
  [ -S "$socket_path" ] || printf '  %s\n' "$socket_path" >&2
done
exit 1
