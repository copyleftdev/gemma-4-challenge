#!/usr/bin/env sh
set -eu

COMPOSE="${DOCKER_COMPOSE:-docker compose}"
MODEL="${CARE_COMPASS_MODEL:-gemma4:e2b}"
PORT="${CARE_COMPASS_PORT:-8080}"
OPEN_BROWSER="${OPEN_BROWSER:-1}"
OLLAMA_MODE="${OLLAMA_MODE:-container}"
OLLAMA_GPU="${OLLAMA_GPU:-auto}"
WAIT_SECONDS="${DEMO_WAIT_SECONDS:-120}"

notice() {
  printf '%s\n' "$*"
}

run_compose() {
  # shellcheck disable=SC2086
  $COMPOSE "$@"
}

host_ollama_ready() {
  command -v ollama >/dev/null 2>&1 && ollama list >/dev/null 2>&1
}

host_gpu_ready() {
  command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1
}

docker_gpu_ready() {
  docker info --format '{{json .Runtimes}}' 2>/dev/null | grep -iq nvidia \
    || command -v nvidia-container-cli >/dev/null 2>&1 \
    || command -v nvidia-ctk >/dev/null 2>&1
}

configure_gpu_compose() {
  if [ "$OLLAMA_MODE" = "host" ]; then
    return 0
  fi
  if [ "$OLLAMA_GPU" = "0" ]; then
    notice "Dockerized Ollama GPU access disabled."
    return 0
  fi
  if [ "$OLLAMA_GPU" = "1" ] || {
    [ "$OLLAMA_GPU" = "auto" ] && host_gpu_ready && docker_gpu_ready
  }; then
    COMPOSE="$COMPOSE -f docker-compose.yml -f docker-compose.gpu.yml"
    notice "Requesting NVIDIA GPU access for Dockerized Ollama."
  elif [ "$OLLAMA_GPU" = "auto" ] && host_gpu_ready; then
    notice "NVIDIA GPU detected, but Docker GPU support was not confirmed; using CPU."
  fi
}

port_is_free() {
  if ! command -v python3 >/dev/null 2>&1; then
    return 0
  fi
  python3 - "$1" <<'PY'
import socket
import sys

with socket.socket() as sock:
    try:
        sock.bind(("127.0.0.1", int(sys.argv[1])))
    except OSError:
        raise SystemExit(1)
PY
}

choose_port() {
  existing_port="$(
    run_compose port care-compass 8080 2>/dev/null | awk -F: 'END {print $NF}'
  )"
  if [ -n "$existing_port" ]; then
    PORT="$existing_port"
    export CARE_COMPASS_PORT="$PORT"
    if [ -z "${DEMO_URL:-}" ]; then
      URL="http://127.0.0.1:${PORT}"
    else
      URL="$DEMO_URL"
    fi
    notice "Reusing Care Compass port ${PORT}."
    return 0
  fi

  candidate="$PORT"
  while ! port_is_free "$candidate"; do
    candidate=$((candidate + 1))
  done
  if [ "$candidate" != "$PORT" ]; then
    notice "Port ${PORT} is busy; using ${candidate} instead."
  fi
  PORT="$candidate"
  export CARE_COMPASS_PORT="$PORT"
  if [ -z "${DEMO_URL:-}" ]; then
    URL="http://127.0.0.1:${PORT}"
  else
    URL="$DEMO_URL"
  fi
}

wait_for_container_ollama() {
  elapsed=0
  while [ "$elapsed" -lt "$WAIT_SECONDS" ]; do
    if run_compose exec -T ollama ollama list >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  notice "Timed out waiting for the Ollama container."
  return 1
}

wait_for_demo() {
  elapsed=0
  while [ "$elapsed" -lt "$WAIT_SECONDS" ]; do
    if curl -fsS "${URL}/api/status" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  notice "Timed out waiting for Care Compass at ${URL}."
  return 1
}

open_demo() {
  if [ "$OPEN_BROWSER" = "0" ]; then
    return 0
  fi

  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL" >/dev/null 2>&1 &
    return 0
  fi
  if command -v open >/dev/null 2>&1; then
    open "$URL" >/dev/null 2>&1 &
    return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    python3 -m webbrowser "$URL" >/dev/null 2>&1 &
    return 0
  fi

  notice "Browser opener not found. Open ${URL} manually."
}

if [ "${DEMO_PREFLIGHT:-1}" != "0" ]; then
  scripts/doctor.sh
fi
configure_gpu_compose
run_compose version >/dev/null
choose_port

if [ "$OLLAMA_MODE" = "host" ] || {
  [ "$OLLAMA_MODE" = "auto" ] && host_ollama_ready
}; then
  notice "Using host Ollama at http://host.docker.internal:11434"
  ollama pull "$MODEL"
  export CARE_COMPASS_OLLAMA_HOST="http://host.docker.internal:11434"
else
  notice "Using Dockerized Ollama"
  run_compose up -d ollama
  wait_for_container_ollama
  run_compose exec -T ollama ollama pull "$MODEL"
  export CARE_COMPASS_OLLAMA_HOST="http://ollama:11434"
fi

export CARE_COMPASS_MODEL="$MODEL"

notice "Starting Care Compass on ${URL}"
run_compose up -d --build care-compass
wait_for_demo
open_demo

notice "Care Compass is ready: ${URL}"
notice "Model: ${MODEL}"
