#!/usr/bin/env bash
# Build the native GNOME applet; no glibc runtime is needed.
set -euo pipefail
project=$(cd -- "$(dirname -- "$0")/.." && pwd)
output=${OUTPUT_DIR:-$project/out}
mkdir -p "$output"
output=$(cd "$output" && pwd)
podman run --rm \
  --volume "$project/packaging:/recipe:ro" --volume "$output:/out" \
  docker.io/library/alpine:3.22 sh /recipe/build-in-container.sh tailscale-qs
