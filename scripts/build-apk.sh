#!/usr/bin/env bash
# Package a locally built runtime. The signing key stays in ignored out/private.
set -euo pipefail
project=$(cd -- "$(dirname -- "$0")/.." && pwd)
output=${OUTPUT_DIR:-$project/out}
[[ $(uname -m) == aarch64 ]] || { echo 'This build script currently requires a native aarch64 host.' >&2; exit 1; }
mkdir -p "$output"
output=$(cd "$output" && pwd)
[[ -f $output/runtime.tar.zst && -f $output/runtime.sha256 ]] || { echo 'Run scripts/build-runtime.sh first.' >&2; exit 1; }
# The manifest uses only the digest; allow moving the output directory.
read -r digest _ < "$output/runtime.sha256"
printf '%s  %s\n' "$digest" "$output/runtime.tar.zst" | sha256sum --check -
podman run --rm \
  --volume "$project/packaging:/recipe:ro" --volume "$output:/out" \
  docker.io/library/alpine:3.22 sh /recipe/build-in-container.sh
