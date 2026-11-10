FROM debian:stable-slim

RUN <<'EOF'
set -xe
apt-get update
apt-get install -y --no-install-recommends ostree ca-certificates
rm -rf /var/lib/apt/lists/*
EOF

COPY sync.sh /usr/local/bin/sync-ostree
RUN chmod 0755 /usr/local/bin/sync-ostree

WORKDIR /tmp
ENTRYPOINT ["sync-ostree"]
