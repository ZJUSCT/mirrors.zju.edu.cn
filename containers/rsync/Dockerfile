FROM debian:stable-slim

RUN <<'EOF'
set -xe
apt-get update
apt-get install -y --no-install-recommends rsync
rm -rf /var/lib/apt/lists/*
EOF
