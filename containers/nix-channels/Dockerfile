FROM python:3-slim

RUN <<'EOF'
set -xe
groupadd --gid 65532 mirror
useradd --uid 65532 --gid 65532 --home-dir /tmp --no-create-home --shell /usr/sbin/nologin mirror
EOF

RUN python -m pip install --no-cache-dir beautifulsoup4 "httpx2[http2]" pydantic-settings tenacity

COPY --chmod=0644 nix-channels.py /usr/local/lib/nix-channels.py

ENV HOME=/tmp
WORKDIR /data
USER 65532:65532
