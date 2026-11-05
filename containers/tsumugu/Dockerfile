FROM rust:1-trixie AS builder

RUN cargo install tsumugu --locked --root /out

FROM debian:stable-slim

RUN <<'EOF'
set -xe
apt-get update
apt-get install -y --no-install-recommends ca-certificates libgcc-s1
rm -rf /var/lib/apt/lists/*
EOF

COPY --from=builder /out/bin/tsumugu /usr/local/bin/tsumugu

WORKDIR /tmp
