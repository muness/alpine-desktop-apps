#!/bin/sh
set -eu
apk add --no-cache abuild alpine-sdk zstd tar pigz
# abuild resolves its virtual build dependencies from these indexes.
apk update
adduser -D builder
addgroup builder abuild
mkdir -p /home/builder/work/desktop-apps /home/builder/.abuild /out/apk /out/keys /out/private
chmod 700 /out/private
cp /recipe/APKBUILD /recipe/desktop-apps-runtime /recipe/1password /recipe/chatgpt \
 /recipe/browseros-neo /recipe/browseros-neo.desktop /recipe/onepassword.desktop /recipe/chatgpt.desktop /home/builder/work/desktop-apps/
# This is a local generated input, never an unchecked remote source.
ln -s /out/runtime.tar.zst /home/builder/work/desktop-apps/runtime.tar.zst
chown -R builder:builder /home/builder
if [ -f /out/private/packager.rsa ]; then
 cp /out/private/packager.rsa /out/keys/packager.rsa.pub /home/builder/.abuild/
else
 su builder -c 'abuild-keygen -a -n'
 key=$(find /home/builder/.abuild -name '*.rsa' | head -1)
 test -n "$key"
 mv "$key" /home/builder/.abuild/packager.rsa
 mv "$key.pub" /home/builder/.abuild/packager.rsa.pub
fi
printf '%s\n' 'PACKAGER_PRIVKEY="/home/builder/.abuild/packager.rsa"' \
 'REPODEST="/home/builder/packages"' > /home/builder/.abuild/abuild.conf
chown -R builder:builder /home/builder/.abuild
# Keep the key even if a build fails, and trust it only in this container.
cp /home/builder/.abuild/packager.rsa /out/private/
chmod 600 /out/private/packager.rsa
cp /home/builder/.abuild/packager.rsa.pub /out/keys/
cp /home/builder/.abuild/packager.rsa.pub /etc/apk/keys/
su builder -c 'cd /home/builder/work/desktop-apps && abuild checksum && abuild -r'
find /home/builder/packages -name '*.apk' -exec cp '{}' /out/apk/ ';'
for package in /out/apk/*.apk; do
 apk --repositories-file /dev/null --keys-dir /out/keys verify "$package"
done
printf '\nAPKs: /out/apk\nPublic key: /out/keys/packager.rsa.pub\nKeep /out/private private.\n'
