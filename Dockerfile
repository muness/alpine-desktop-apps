FROM docker.io/library/debian@sha256:62bd423aeee912639ca8ee681c2b762cb3e25137e0a92b20be455898a9f034ad
COPY chatgpt.deb /tmp/chatgpt.deb
COPY browseros-neo.deb /tmp/browseros-neo.deb
COPY 1password.tar.gz /tmp/1password.tar.gz
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    /tmp/chatgpt.deb /tmp/browseros-neo.deb libsecret-1-0 libgtk-3-0t64 libnss3 libasound2t64 libgbm1 \
    libgl1-mesa-dri libxss1 libxtst6 libnotify4 libxkbcommon0 xdg-utils \
    libglib2.0-bin dbus-bin dbus-user-session ca-certificates fonts-dejavu-core \
    python3 git procps \
 && useradd -u 10000 -m -s /bin/bash appuser \
 && mkdir -p /opt/1Password /usr/share/desktop-directories \
 && tar -xzf /tmp/1password.tar.gz --strip-components=1 -C /opt/1Password \
 && /opt/1Password/after-install.sh \
 && mkdir -p /run/user/10000 /run/dbus \
 && touch /etc/machine-id /etc/resolv.conf \
 && rm /tmp/chatgpt.deb /tmp/browseros-neo.deb /tmp/1password.tar.gz \
 && apt-get clean
COPY portal-xdg-open /usr/local/bin/xdg-open
RUN chmod 755 /usr/local/bin/xdg-open
