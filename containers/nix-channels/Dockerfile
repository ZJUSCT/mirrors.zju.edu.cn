FROM debian:stable-slim

RUN <<'EOF'
set -xe
apt-get update
apt-get install -y --no-install-recommends ca-certificates nix-bin python3 python3-venv python3-pyquery python3-pytz python3-requests patch
rm -rf /var/lib/apt/lists/*
python3 -m venv --system-site-packages /opt/venv
/opt/venv/bin/pip install --no-cache-dir minio
groupadd --gid 65532 mirror
useradd --uid 65532 --gid 65532 --home-dir /tmp --no-create-home --shell /usr/sbin/nologin mirror
EOF

ADD https://raw.githubusercontent.com/tuna/tunasync-scripts/master/nix-channels.py \
    /usr/local/src/nix-channels/upstream.py
COPY mirror.patch /usr/local/src/nix-channels/mirror.patch
RUN <<'EOF'
set -xe
cp /usr/local/src/nix-channels/upstream.py /usr/local/lib/nix-channels.py
patch --batch --fuzz=0 /usr/local/lib/nix-channels.py /usr/local/src/nix-channels/mirror.patch
chmod 0644 /usr/local/lib/nix-channels.py /usr/local/src/nix-channels/upstream.py
EOF

ENV PATH="/opt/venv/bin:${PATH}" HOME=/tmp TUNASYNC_WORKING_DIR=/data \
    NIX_CONFIG="experimental-features = nix-command"
WORKDIR /data
USER 65532:65532
