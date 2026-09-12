#!/usr/bin/env bash
# jcr-daemon.sh — start|stop|restart|status for the JCR core daemon.
#
# Why a script: starting a long-running server from an interactive shell is
# fragile (backgrounding, self-matching pkill patterns). Encapsulating it here
# makes start/stop reliable and gives the harness a stable endpoint.
#
# Env: JCR_HOME (default ~/.local/share/jcr), JCR_PORT (8765), JCR_PYTHON.
set -euo pipefail

JCR_HOME="${JCR_HOME:-$HOME/.local/share/jcr}"
JCR_PORT="${JCR_PORT:-8765}"
JCR_HOST="${JCR_HOST:-127.0.0.1}"
JCR_PYTHON="${JCR_PYTHON:-python3}"
PIDFILE="$JCR_HOME/daemon.pid"
LOG="$JCR_HOME/daemon.log"
PATTERN="jcr_core[.]daemon"

mkdir -p "$JCR_HOME"

is_up() { curl -sf --max-time 2 "http://$JCR_HOST:$JCR_PORT/health" >/dev/null 2>&1; }

start() {
  if is_up; then echo "already running on $JCR_HOST:$JCR_PORT"; return 0; fi
  setsid -f env JCR_HOME="$JCR_HOME" JCR_PORT="$JCR_PORT" JCR_HOST="$JCR_HOST" \
    "$JCR_PYTHON" -u -m jcr_core.daemon </dev/null >"$LOG" 2>&1
  for _ in $(seq 1 20); do
    if is_up; then
      pgrep -f "$PATTERN" >"$PIDFILE" 2>/dev/null || true
      echo "jcr-daemon up on $JCR_HOST:$JCR_PORT (pid $(head -1 "$PIDFILE" 2>/dev/null))"
      return 0
    fi
    sleep 0.25
  done
  echo "failed to start; last log lines:" >&2
  tail -n 20 "$LOG" >&2 || true
  return 1
}

stop() {
  local stopped=0
  if [ -f "$PIDFILE" ]; then
    while read -r pid; do
      [ -n "$pid" ] && kill "$pid" 2>/dev/null && stopped=1 || true
    done <"$PIDFILE"
    rm -f "$PIDFILE"
  fi
  # safety net: match the module, not this script (the pattern is in-file, so it
  # cannot match our own command line)
  pkill -f "$PATTERN" 2>/dev/null && stopped=1 || true
  if [ "$stopped" = 1 ]; then echo "jcr-daemon stopped"; else echo "jcr-daemon was not running"; fi
}

status() {
  if is_up; then
    echo "running on $JCR_HOST:$JCR_PORT"
    curl -s --max-time 3 "http://$JCR_HOST:$JCR_PORT/state" || true
    echo
  else
    echo "not running"
    return 1
  fi
}

case "${1:-status}" in
  start) start ;;
  stop) stop ;;
  restart) stop; sleep 0.3; start ;;
  status) status ;;
  *) echo "usage: $0 start|stop|restart|status" >&2; exit 2 ;;
esac
