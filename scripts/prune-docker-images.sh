#!/usr/bin/env bash
# Reclaim Docker Desktop disk space by removing unused images and build cache.
# Does NOT touch volumes - named or anonymous - since those may hold data
# (e.g. grandflow_data) or be awaiting manual review before deletion.
#
# Usage: ./scripts/prune-docker-images.sh [max-age]
#        max-age defaults to 168h (7 days), passed to --filter until=
set -euo pipefail

MAX_AGE="${1:-168h}"

echo "Disk usage before:"
docker system df

echo
echo "Removing dangling/unused images older than ${MAX_AGE}..."
docker image prune -a --force --filter "until=${MAX_AGE}"

echo
echo "Removing build cache older than ${MAX_AGE}..."
docker builder prune --force --filter "until=${MAX_AGE}"

echo
echo "Disk usage after:"
docker system df
