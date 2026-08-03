#!/bin/sh
set -eu

project="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
python="${PYTHON:-$project/.venv/bin/python}"

cd "$project"

test -x "$python" || {
  echo "ERROR: Python no disponible: $python" >&2
  exit 1
}

echo "=== Sintaxis Python ==="
"$python" -m compileall -q backend tests

echo "=== Sintaxis de scripts ==="
for script in scripts/*.sh
do
  sh -n "$script"
done

echo "=== Sintaxis JavaScript ==="
if command -v node >/dev/null 2>&1
then
  node --check frontend/app.js
elif command -v docker >/dev/null 2>&1
then
  docker run --rm \
    -v "$project/frontend:/app:ro" \
    -w /app \
    node:22-alpine \
    node --check app.js
else
  echo "ERROR: se necesita Node.js o Docker" >&2
  exit 1
fi

echo "=== Pruebas automatizadas ==="
"$python" -m unittest discover -s tests -p 'test_*.py' -v

echo "=== Contratos públicos ==="
"$python" tests/validate_contracts.py

echo "=== Integridad Git ==="
git --no-pager diff --check

echo "RESULTADO: validación completa correcta."
