#!/usr/bin/env bash
set -euo pipefail

PY=python3
VENV=.venv
REQS=docs/requirements.txt

PORT=${PORT:-8000}

usage(){
  echo "Usage: $0 [build|serve|install]" >&2
  exit 2
}

if [ "$#" -gt 1 ]; then
  usage
fi

CMD=${1:-serve}

if [ ! -f "$REQS" ]; then
  echo "Requirements file not found: $REQS" >&2
  exit 1
fi

if [ ! -d "$VENV" ]; then
  echo "Creating virtualenv at $VENV"
  $PY -m venv "$VENV"
fi

# shellcheck disable=SC1091
source "$VENV/bin/activate"

pip install --upgrade pip
pip install -r "$REQS"

get_free_port() {
  local start_port="${1:-8000}"
  "$PY" -c "
import socket
start = $start_port
for p in range(start, start + 100):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('127.0.0.1', p))
            print(p)
            break
        except OSError:
            continue
"
}

case "$CMD" in
  build)
    echo "Building mkdocs site..."
    "$VENV/bin/mkdocs" build --strict
    ;;
  serve)
    FREE_PORT=$(get_free_port "$PORT")
    if [ "$FREE_PORT" != "$PORT" ]; then
      echo "Port $PORT is in use. Using next available port: $FREE_PORT"
    fi
    echo "Starting mkdocs serve (http://127.0.0.1:${FREE_PORT})..."
    "$VENV/bin/mkdocs" serve -a "127.0.0.1:${FREE_PORT}"
    ;;
  install)
    echo "Installed documentation dependencies into $VENV"
    ;;
  *)
    usage
    ;;
esac
