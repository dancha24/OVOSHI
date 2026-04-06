#!/usr/bin/env sh
# Разработка: код с хоста в контейнерах; с доменом: ./dev.sh --domain up -d --build
set -e
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ "$1" = "--domain" ]; then
  shift
  exec docker compose -f "$HERE/docker-compose.yml" -f "$HERE/docker-compose.dev.yml" -f "$HERE/docker-compose.domain.yml" "$@"
fi
exec docker compose -f "$HERE/docker-compose.yml" -f "$HERE/docker-compose.dev.yml" "$@"
