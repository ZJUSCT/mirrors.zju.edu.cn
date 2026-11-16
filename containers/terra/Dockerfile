FROM debian:stable-slim

RUN <<'EOF'
set -xe
apt-get update
apt-get install -y --no-install-recommends bash rsync openssl ca-certificates python3
rm -rf /var/lib/apt/lists/*
EOF

# 官方同步脚本及其 MIT 许可证，固定版本并校验下载内容。
ADD --chmod=0755 --checksum=sha256:c7be5c8a1bc5ca21e07d28f90bcc6b4caf8dc5ec3e00eefdb6c96dcc92504a9e \
    https://raw.githubusercontent.com/terrapkg/mirror-script/aa1e220eafb1a90280ef4b3906b3bc53a2610fae/mirror.sh \
    /usr/local/lib/terra/mirror.sh
ADD --chmod=0644 --checksum=sha256:0e19651e5af3c518ae7e3507c5f500e1a80aba7f96c28bafd4bdff197eb9c5fb \
    https://raw.githubusercontent.com/terrapkg/mirror-script/aa1e220eafb1a90280ef4b3906b3bc53a2610fae/LICENSE \
    /usr/share/doc/terra-mirror/LICENSE
COPY --chmod=0755 terra-rsync.sh /usr/local/bin/terra-rsync
COPY --chmod=0644 sync.py /usr/local/lib/terra/sync.py

ENV HOME=/tmp
ENV MIRROR_DIR=/data RSYNC=/usr/local/bin/terra-rsync PARALLEL=0 USE_RCLONE=0 SYNC_SOURCES=1
WORKDIR /data
USER 65532:65532
ENTRYPOINT ["python3", "/usr/local/lib/terra/sync.py"]
