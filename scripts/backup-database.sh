#!/bin/sh
set -eu
umask 0077

project="/srv/mesh-noroeste"
database="$project/state/mesh-noroeste.db"
backup_dir="$project/state/backups"
lock_file="/run/lock/mesh-noroeste-update.lock"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
name="mesh-noroeste.db.$stamp.sqlite3"
target="$backup_dir/$name"
temporary="$backup_dir/.$name.tmp"
checksum="$target.sha256"
checksum_tmp="$checksum.tmp"

mkdir -p "$backup_dir"

exec 9>"$lock_file"
flock -w 300 9

[ -f "$database" ] || {
  printf 'ERROR: non existe %s\n' "$database" >&2
  exit 1
}

trap 'rm -f -- "$temporary" "$checksum_tmp"' EXIT HUP INT TERM

sqlite3 "$database" "VACUUM INTO '$temporary';"

[ "$(sqlite3 "$temporary" 'PRAGMA quick_check;')" = "ok" ] || {
  printf 'ERROR: quick_check fallou\n' >&2
  exit 1
}

hash="$(sha256sum "$temporary" | awk '{print $1}')"
printf '%s  %s\n' "$hash" "$name" > "$checksum_tmp"

mv -- "$temporary" "$target"
mv -- "$checksum_tmp" "$checksum"

find "$backup_dir" -maxdepth 1 -type f \
  \( -name 'mesh-noroeste.db.*.sqlite3' \
     -o -name 'mesh-noroeste.db.*.sqlite3.sha256' \) \
  -mmin +43200 -print -delete

printf 'Backup correcto: %s\n' "$target"
