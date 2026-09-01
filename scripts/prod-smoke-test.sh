#!/usr/bin/env bash
# ==============================================================================
# NEXUS - production stack smoke test
#
# Builds and starts docker-compose.prod.yml with CI-safe DUMMY values, waits for
# every service to become healthy, checks the important endpoints (including the
# DB-down readiness behaviour), then tears everything down - containers, volume
# and built images.
#
# Deterministic and timeout-bounded. Exit code 0 == the production stack builds
# and is internally valid. No real secrets, no registry push, no deploy.
#
#   Usage:  ./scripts/prod-smoke-test.sh
# ==============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILE="${REPO_ROOT}/docker-compose.prod.yml"
PROJECT="nexus_smoke"
PROXY_PORT="${SMOKE_PROXY_PORT:-8091}"
BASE_URL="http://127.0.0.1:${PROXY_PORT}"
HEALTH_TIMEOUT="${SMOKE_HEALTH_TIMEOUT:-240}"

# --- CI-safe dummy configuration (NOT secrets) --------------------------------
export SECRET_KEY="smoke-test-only-$(head -c16 /dev/urandom | od -An -tx1 | tr -d ' \n')"
export ALLOWED_HOSTS="localhost,127.0.0.1,backend,proxy"
export CSRF_TRUSTED_ORIGINS="${BASE_URL}"
export SECURE_SSL_REDIRECT="false"   # plain HTTP in the test harness
export SECURE_HSTS_SECONDS="0"
export DB_NAME="nexus_smoke"
export DB_USER="nexus_smoke"
export DB_PASSWORD="smoke-test-db-password"
export PROXY_PORT
export VITE_API_URL="/api/v1"

DC() { docker compose -p "${PROJECT}" -f "${COMPOSE_FILE}" "$@"; }

cleanup() {
  echo "--- tearing down ---"
  DC down -v --remove-orphans --rmi local >/dev/null 2>&1 || true
}
trap cleanup EXIT

fail() { echo "SMOKE FAIL: $*" >&2; exit 1; }

wait_healthy() {
  local svc="$1" deadline status cid
  deadline=$(( $(date +%s) + HEALTH_TIMEOUT ))
  while :; do
    cid="$(DC ps -q "${svc}" 2>/dev/null || true)"
    if [ -n "${cid}" ]; then
      status="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "${cid}" 2>/dev/null || echo unknown)"
      [ "${status}" = "healthy" ] && { echo "  ${svc}: healthy"; return 0; }
    fi
    if [ "$(date +%s)" -ge "${deadline}" ]; then
      DC logs "${svc}" | tail -n 40 >&2 || true
      fail "${svc} did not become healthy within ${HEALTH_TIMEOUT}s (last: ${status:-none})"
    fi
    sleep 3
  done
}

expect_code() {
  local path="$1" want="$2" got
  got="$(curl -s -o /dev/null -w '%{http_code}' "${BASE_URL}${path}" || true)"
  [ "${got}" = "${want}" ] || fail "GET ${path} -> ${got}, expected ${want}"
  echo "  GET ${path} -> ${got}"
}

echo "--- building & starting the production stack (project ${PROJECT}) ---"
DC up -d --build

echo "--- waiting for health ---"
wait_healthy db
wait_healthy backend
wait_healthy proxy

echo "--- endpoint checks (through the nginx proxy) ---"
expect_code /health/                      200
expect_code /health/ready/                200
expect_code /api/health/                  200
expect_code /                             200
expect_code /x/deep-link                  200   # SPA fallback
expect_code /static/admin/css/base.css    200   # WhiteNoise
expect_code /api/v1/orders/               401   # protected API stays unauthenticated
expect_code /api/v1/dashboard/            401   # aggregation endpoint also requires auth

echo "--- correlation id ---"
rid="$(curl -s -o /dev/null -D - "${BASE_URL}/health/" | tr -d '\r' | awk 'tolower($1)=="x-request-id:"{print $2}')"
[ -n "${rid}" ] || fail "no X-Request-ID header on /health/"
echo "  generated X-Request-ID: ${rid}"

# A client-supplied, well-formed ID must survive nginx -> Gunicorn -> Django.
supplied="smoke-corr-0001"
echoed="$(curl -s -o /dev/null -D - -H "X-Request-ID: ${supplied}" "${BASE_URL}/api/health/" | tr -d '\r' | awk 'tolower($1)=="x-request-id:"{print $2}')"
[ "${echoed}" = "${supplied}" ] || fail "supplied X-Request-ID not preserved (got '${echoed}')"
echo "  preserved X-Request-ID: ${echoed}"

echo "--- DB failure behaviour ---"
DC stop db >/dev/null
sleep 3
expect_code /health/         200   # liveness unaffected
expect_code /health/ready/   503   # readiness reports the outage
DC start db >/dev/null

echo "--- structured logging ---"
# The readiness failure above emits a WARNING through the app logger.
DC logs backend 2>/dev/null | grep -q '"logger":.*"message":' \
  || fail "backend logs are not JSON-structured"
DC logs backend 2>/dev/null | grep -Ei 'authorization|"cookie"|refresh-token|bearer ' \
  && fail "backend logs appear to contain sensitive data" || true
echo "  backend emits JSON logs, no obvious secrets"

echo
echo "SMOKE PASS"
