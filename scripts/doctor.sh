#!/usr/bin/env sh
set -u

COMPOSE="${DOCKER_COMPOSE:-docker compose}"
MODEL="${CARE_COMPASS_MODEL:-gemma4:e2b}"
PORT="${CARE_COMPASS_PORT:-8080}"
OPEN_BROWSER="${OPEN_BROWSER:-1}"
OLLAMA_MODE="${OLLAMA_MODE:-container}"
OLLAMA_GPU="${OLLAMA_GPU:-auto}"

errors=0
warnings=0
docker_cli=0
docker_daemon=0

say() {
  printf '%s\n' "$*"
}

pass() {
  say "OK    $*"
}

info() {
  say "INFO  $*"
}

warn() {
  warnings=$((warnings + 1))
  say "WARN  $*"
}

fail() {
  errors=$((errors + 1))
  say "FAIL  $*"
}

run_compose() {
  # shellcheck disable=SC2086
  $COMPOSE "$@"
}

command_required() {
  if command -v "$1" >/dev/null 2>&1; then
    pass "$2"
  else
    fail "$3"
  fi
}

command_recommended() {
  if command -v "$1" >/dev/null 2>&1; then
    pass "$2"
  else
    warn "$3"
  fi
}

host_gpu_ready() {
  command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1
}

docker_gpu_ready() {
  if [ "$docker_daemon" -ne 1 ]; then
    return 1
  fi
  docker info --format '{{json .Runtimes}}' 2>/dev/null | grep -iq nvidia \
    || command -v nvidia-container-cli >/dev/null 2>&1 \
    || command -v nvidia-ctk >/dev/null 2>&1
}

browser_opener_ready() {
  command -v xdg-open >/dev/null 2>&1 \
    || command -v open >/dev/null 2>&1 \
    || command -v python3 >/dev/null 2>&1
}

check_disk() {
  if ! command -v awk >/dev/null 2>&1; then
    warn "Skipping disk-space check because awk is missing."
    return
  fi
  available_kb="$(df -Pk . 2>/dev/null | awk 'NR == 2 {print $4}')"
  if [ -z "$available_kb" ]; then
    warn "Could not check free disk space."
    return
  fi
  if [ "$available_kb" -lt 20971520 ]; then
    warn "Less than 20 GB free in this filesystem. First Docker/Ollama setup may fail."
  else
    pass "At least 20 GB free disk space is available."
  fi
}

check_memory() {
  if ! command -v awk >/dev/null 2>&1; then
    warn "Skipping memory check because awk is missing."
    return
  fi
  if [ ! -r /proc/meminfo ]; then
    info "Could not check system memory on this OS."
    return
  fi
  mem_kb="$(awk '/MemTotal/ {print $2}' /proc/meminfo)"
  if [ -z "$mem_kb" ]; then
    warn "Could not read total system memory."
    return
  fi
  if [ "$mem_kb" -lt 16777216 ]; then
    warn "Less than 16 GB RAM detected. CPU fallback may be slow or unstable."
  else
    pass "At least 16 GB system RAM is available."
  fi
}

say "Care Compass preflight"
say "Model: ${MODEL}"
say "Port: ${PORT}"
say "Ollama mode: ${OLLAMA_MODE}"
say "GPU mode: ${OLLAMA_GPU}"
say ""
say "Required checks"

if command -v docker >/dev/null 2>&1; then
  docker_cli=1
  pass "Docker CLI is installed."
else
  fail "Docker CLI is missing. Install Docker Desktop or Docker Engine."
fi

if [ "$docker_cli" -eq 1 ]; then
  if docker info >/dev/null 2>&1; then
    docker_daemon=1
    pass "Docker daemon is running and accessible."
  else
    fail "Docker daemon is not accessible. Start Docker or fix user permissions."
  fi
fi

if [ "$docker_cli" -eq 1 ]; then
  if run_compose version >/dev/null 2>&1; then
    pass "Docker Compose plugin is available."
  else
    fail "Docker Compose plugin is missing. Install Docker Compose v2."
  fi
fi

command_required curl "curl is installed." "curl is missing. Install curl for readiness checks."
command_required awk "awk is installed." "awk is missing. Install awk for port discovery."

say ""
say "Capacity checks"
check_disk
check_memory
info "First run may download the Ollama image, the Gemma model, and build the app image."

say ""
say "Runtime checks"
if [ "$OLLAMA_MODE" = "host" ]; then
  if command -v ollama >/dev/null 2>&1; then
    if ollama list >/dev/null 2>&1; then
      pass "Host Ollama is installed and reachable locally."
    else
      fail "Host Ollama is installed but not responding. Start `ollama serve`."
    fi
  else
    fail "OLLAMA_MODE=host requires the ollama CLI and a running host daemon."
  fi
  info "Host Ollama must be reachable by Docker at http://host.docker.internal:11434."
else
  pass "Dockerized Ollama will be started by the demo."
fi

if [ "$OLLAMA_MODE" != "host" ]; then
  if [ "$OLLAMA_GPU" = "0" ]; then
    info "GPU access is disabled; Dockerized Ollama will use CPU."
  elif host_gpu_ready; then
    pass "NVIDIA GPU driver is visible on the host."
    if docker_gpu_ready; then
      pass "Docker NVIDIA runtime/toolkit signal is present."
    elif [ "$OLLAMA_GPU" = "1" ]; then
      fail "OLLAMA_GPU=1 requested, but Docker GPU support was not detected."
    else
      warn "NVIDIA GPU exists, but Docker GPU support was not detected. CPU fallback will be used unless the NVIDIA Container Toolkit is installed."
    fi
  elif [ "$OLLAMA_GPU" = "1" ]; then
    fail "OLLAMA_GPU=1 requested, but `nvidia-smi` did not find a usable NVIDIA GPU."
  else
    warn "No NVIDIA GPU detected. The demo can run on CPU, but model responses will be slower."
  fi
fi

if [ "$OPEN_BROWSER" = "0" ]; then
  info "Browser opening is disabled by OPEN_BROWSER=0."
elif browser_opener_ready; then
  pass "A browser opener is available."
else
  warn "No browser opener found. The demo will print the URL for manual opening."
fi

say ""
if [ "$errors" -gt 0 ]; then
  say "Preflight failed with ${errors} error(s) and ${warnings} warning(s)."
  say "Fix the failed requirements, then rerun `make doctor` or `make demo`."
  exit 1
fi

if [ "$warnings" -gt 0 ]; then
  say "Preflight completed with ${warnings} warning(s)."
else
  say "Preflight passed."
fi
