#!/usr/bin/env bash
set -euo pipefail

uv sync --quiet
uv run pytest -q
uv run jev-review doctor --quiet
