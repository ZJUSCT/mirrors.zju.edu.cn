# Proxmox VE 镜像端到端测试：官方 debian slim 容器 + pve-no-subscription
# 源指向镜像。GPG key 从官方 download.proxmox.com 引导
# （proxmox-release-trixie.asc，与 PVE 官方文档一致）；此后签名校验与
# 下载全程走镜像。只做 download（pve-manager 依赖重，安装意义有限）。
FROM python:3.12-slim AS ca
FROM debian:stable-slim
COPY --from=ca /etc/ssl/certs /etc/ssl/certs
RUN mkdir -p /usr/lib/ssl \
    && ln -s /etc/ssl/certs /usr/lib/ssl/certs \
    && ln -s /etc/ssl/certs/ca-certificates.crt /usr/lib/ssl/cert.pem
RUN apt-get update && apt-get install -y --no-install-recommends curl gpg \
    && rm -rf /var/lib/apt/lists/*
COPY --chmod=755 e2e.sh /e2e.sh
ENTRYPOINT ["/e2e.sh"]
