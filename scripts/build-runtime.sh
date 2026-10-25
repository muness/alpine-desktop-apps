#!/usr/bin/env bash
# Build the experiment; never deploy to a host or tablet.
set -euo pipefail
project=$(cd -- "$(dirname -- "$0")/.." && pwd)
output=${OUTPUT_DIR:-$project/out}
[[ $(uname -m) == aarch64 ]] || { echo 'This build script currently requires a native aarch64 host.' >&2; exit 1; }
mkdir -p "$output/cache"
output=$(cd "$output" && pwd)
fetch() {
  local name=$1 url=$2 digest=$3
  if [[ ! -f $output/cache/$name ]]; then
    curl --fail --location --retry 3 --proto '=https' --proto-redir '=https' \
      --output "$output/cache/$name.part" "$url"
    mv "$output/cache/$name.part" "$output/cache/$name"
  fi
  printf '%s  %s\n' "$digest" "$output/cache/$name" | sha256sum --check -
}
fetch 1password.tar.gz \
  https://downloads.1password.com/linux/tar/stable/aarch64/1password-8.12.42.arm64.tar.gz \
  b6e29499bafb298a992bd91829806461a44ab6dbcf4036de3cbebdd2fee8fd28
fetch chatgpt.deb \
  https://persistent.oaistatic.com/codex-app-prod/linux/deb/pool/main/c/chatgpt/chatgpt_26.1016.61520_arm64.deb \
  c5498348581f7607102ac6f206c9f87668cce36c8c7dbb4c0209e25cd8a60b11
context=$(mktemp -d "$output/.runtime-context.XXXXXX")
container=
cleanup() {
  [[ -z $container ]] || podman rm "$container" >/dev/null
  rm -rf -- "$context"
}
trap cleanup EXIT
cp "$output/cache/1password.tar.gz" "$output/cache/chatgpt.deb" "$context/"
cp "$project/packaging/portal-xdg-open" "$context/"
image=localhost/alpine-desktop-apps-experiment:20261025
podman build --no-cache --platform linux/arm64 --file "$project/Dockerfile" --tag "$image" "$context"
container=$(podman create "$image" /bin/true)
podman export "$container" | zstd -T0 -3 > "$output/runtime.tar.zst.part"
mv "$output/runtime.tar.zst.part" "$output/runtime.tar.zst"
sha256sum "$output/runtime.tar.zst" > "$output/runtime.sha256"
printf 'Runtime: %s\nNext: scripts/build-apk.sh\n' "$output/runtime.tar.zst"
