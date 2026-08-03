#!/bin/sh
set -eu

project="/srv/mesh-noroeste"
python="$project/.venv/bin/python"
database="$project/state/mesh-noroeste.db"
lock_file="/run/lock/mesh-noroeste-update.lock"

exec 9>"$lock_file"
flock -w 300 9

cd "$project"

"$python" -m mesh_noroeste.cli \
  --compact \
  prune \
  --database "$database"

"$python" -m mesh_noroeste.cli \
  --compact \
  check \
  --database "$database"
