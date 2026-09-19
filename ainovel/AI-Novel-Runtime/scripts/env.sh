#!/usr/bin/env bash
# Source this before running any --model-provider deepseek command:
#   cd AI-Novel-Runtime && source scripts/env.sh
#
# It does two things:
#   1. Loads the API keys from the repo-root .env into the environment
#      (the shell does NOT export them automatically).
#   2. Adds the DeepSeek/OpenAI hosts to no_proxy so a running Clash-style
#      proxy (http_proxy/https_proxy/all_proxy, e.g. 127.0.0.1:7897) does not
#      hijack the request and reject it with a 403 (httpcore.ProxyError).
#
# The runtime LLM factory also forces a direct (trust_env=False) client for
# DeepSeek, so this is belt-and-suspenders for ad-hoc scripts/curl.

# Resolve the repo root relative to this script, regardless of CWD.
_ANES_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
_ANES_REPO_ROOT="$(cd "${_ANES_SCRIPT_DIR}/.." && pwd)"          # AI-Novel-Runtime
_ANES_ENV_FILE="$(cd "${_ANES_REPO_ROOT}/.." && pwd)/.env"        # repo-root .env

if [ -f "${_ANES_ENV_FILE}" ]; then
  set -a
  # shellcheck disable=SC1090
  . "${_ANES_ENV_FILE}"
  set +a
  echo "[env.sh] loaded keys from ${_ANES_ENV_FILE}"
else
  echo "[env.sh] WARNING: ${_ANES_ENV_FILE} not found; API keys not loaded" >&2
fi

# Keep China-hosted / provider APIs off any ambient proxy.
_ANES_DIRECT_HOSTS="api.deepseek.com,api.openai.com,127.0.0.1,localhost"
if [ -n "${no_proxy}" ]; then
  export no_proxy="${no_proxy},${_ANES_DIRECT_HOSTS}"
else
  export no_proxy="${_ANES_DIRECT_HOSTS}"
fi
export NO_PROXY="${no_proxy}"
echo "[env.sh] no_proxy=${no_proxy}"

unset _ANES_SCRIPT_DIR _ANES_REPO_ROOT _ANES_ENV_FILE _ANES_DIRECT_HOSTS
