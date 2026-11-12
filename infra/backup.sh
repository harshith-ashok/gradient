#!/bin/sh
# Back up Postgres (all accounts, courses, plans and quiz history) and the uploaded syllabi.
#   infra/backup.sh [project] [compose-file]      e.g. infra/backup.sh gradient-prod infra/docker-compose.prod.yml
# Restore: gunzip -c backups/<file>.sql.gz | docker compose -p <project> -f <file> exec -T postgres psql -U gradient gradient
set -eu
PROJECT="${1:-gradient-prod}"
FILE="${2:-$(dirname "$0")/docker-compose.prod.yml}"
OUT="${BACKUP_DIR:-backups}"
STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUT"
docker compose -p "$PROJECT" -f "$FILE" exec -T postgres pg_dump -U gradient --clean --if-exists gradient | gzip > "$OUT/gradient-$STAMP.sql.gz"
docker compose -p "$PROJECT" -f "$FILE" exec -T backend tar -C /data -cz uploads > "$OUT/uploads-$STAMP.tar.gz"
# keep the newest 14 of each
ls -1t "$OUT"/gradient-*.sql.gz 2>/dev/null | tail -n +15 | xargs -r rm -f
ls -1t "$OUT"/uploads-*.tar.gz 2>/dev/null | tail -n +15 | xargs -r rm -f
echo "wrote $OUT/gradient-$STAMP.sql.gz and $OUT/uploads-$STAMP.tar.gz"
