#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONDONTWRITEBYTECODE=1

fail() {
  printf '%s\n' "$1" >&2
  exit 1
}

require_file() {
  [ -f "$1" ] || fail "missing required file: $1"
}

require_file AGENTS.md
require_file CODEPAGER.md
require_file ARCHITECTURE.md
require_file README.md
require_file pyproject.toml
require_file docs/adapter-contract.md
require_file docs/product-story.md
require_file docs/quality.md
require_file docs/runbook.md
require_file docs/exec-plans/active/README.md
require_file docs/exec-plans/active/toolburn-3-phase-plan.md
require_file docs/exec-plans/completed/README.md
require_file src/toolburn/__init__.py
require_file src/toolburn/cli.py
require_file src/toolburn/schema.py
require_file tests/test_cli.py
require_file tests/test_schema.py
require_file scripts/validate.sh

if find . \( -path '*/__pycache__' -o -name '*.pyc' -o -name '.pytest_cache' \) -print | grep -q .; then
  echo "generated Python cache files must not be left in the repo" >&2
  find . \( -path '*/__pycache__' -o -name '*.pyc' -o -name '.pytest_cache' \) -print >&2
  exit 1
fi

python3 - <<'PY'
from pathlib import Path
for path in sorted(Path("src").rglob("*.py")) + sorted(Path("tests").rglob("*.py")):
    compile(path.read_text(encoding="utf-8"), str(path), "exec")
print("python syntax ok")
PY

PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'
PYTHONPATH=src python3 -m toolburn.cli --help >/tmp/toolburn-cli-help.txt
grep -q 'Local-first token burn profiler' /tmp/toolburn-cli-help.txt

tmp_db="$(mktemp -u /tmp/toolburn-validate-XXXXXX.sqlite)"
PYTHONPATH=src python3 -m toolburn.cli schema --db "$tmp_db" >/tmp/toolburn-schema.txt
grep -q '^actors$' /tmp/toolburn-schema.txt
grep -q '^token_events$' /tmp/toolburn-schema.txt
rm -f "$tmp_db"

if grep -RInE 'cp_live_[A-Za-z0-9]+|assistant\.env|telegram|session-key|webhook|BEGIN (RSA|OPENSSH|PRIVATE) KEY|github_pat_' \
  AGENTS.md CODEPAGER.md ARCHITECTURE.md README.md docs scripts src tests pyproject.toml \
  | grep -v '^scripts/validate.sh:' >/tmp/toolburn-secretish.txt; then
  echo "secret-shaped or private-runtime strings found:" >&2
  cat /tmp/toolburn-secretish.txt >&2
  exit 1
fi

echo "toolburn validation ok"
