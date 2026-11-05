FROM debian:stable-slim

RUN <<'EOF'
set -xe
apt-get update
apt-get install -y --no-install-recommends zsh rsync coreutils gawk findutils diffutils grep hostname util-linux patch
rm -rf /var/lib/apt/lists/*
EOF

ADD https://forge.fedoraproject.org/infra/quick-fedora-mirror.git /usr/local/src/qfm
COPY linkstat-rsync3.patch /tmp/linkstat-rsync3.patch
COPY sync-receipt.patch /tmp/sync-receipt.patch
RUN <<'EOF'
set -xe
patch --batch -p1 -d /usr/local/src/qfm < /tmp/linkstat-rsync3.patch
patch --batch -p1 -d /usr/local/src/qfm < /tmp/sync-receipt.patch
install -m 0755 /usr/local/src/qfm/quick-fedora-mirror /usr/local/bin/quick-fedora-mirror
rm -rf /usr/local/src/qfm /tmp/linkstat-rsync3.patch /tmp/sync-receipt.patch
EOF

WORKDIR /tmp
