FROM debian:stable-slim

RUN <<'EOF'
set -xe
apt-get update
apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    patch \
    python3 \
    python3-pyquery \
    python3-pytz \
    python3-requests \
    python3-venv
rm -rf /var/lib/apt/lists/*
groupadd --gid 65532 mirror
useradd --uid 65532 --gid 65532 --home-dir /tmp --no-create-home --shell /usr/sbin/nologin mirror
EOF

RUN <<'EOF'
set -xe
python3 -m venv --system-site-packages /opt/venv
/opt/venv/bin/pip install --no-cache-dir minio
EOF

RUN <<'EOF'
set -xe
curl -fsSL https://artifacts.nixos.org/nix-installer -o /tmp/nix-installer.sh
sh /tmp/nix-installer.sh install linux \
    --extra-conf "sandbox = false" --enable-flakes --init none --no-confirm
rm /tmp/nix-installer.sh
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

ENV PATH="/opt/venv/bin:/nix/var/nix/profiles/default/bin:${PATH}" \
    HOME=/tmp TUNASYNC_WORKING_DIR=/data
WORKDIR /data
USER 65532:65532
