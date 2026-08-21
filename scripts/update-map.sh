#!/bin/sh
set -eu

project="/srv/mesh-noroeste"
python="$project/.venv/bin/python"
database="$project/state/mesh-noroeste.db"
public_dir="$project/frontend/data"
lock_file="/run/lock/mesh-noroeste-update.lock"

mode="${1:-}"

case "$mode" in
  malha|ozulo|meshcore|meshcore-hub)
    ;;
  *)
    echo "Uso: $0 {malha|ozulo|meshcore|meshcore-hub}" >&2
    exit 2
    ;;
esac

exec 9>"$lock_file"
flock -w 300 9

cd "$project"

"$python" -m mesh_noroeste.cli \
  --compact \
  "collect-$mode" \
  --database "$database"

"$python" -m mesh_noroeste.cli \
  --compact \
  check \
  --database "$database"

"$python" -m mesh_noroeste.cli \
  --compact \
  publish \
  --database "$database" \
  --output "$public_dir"
