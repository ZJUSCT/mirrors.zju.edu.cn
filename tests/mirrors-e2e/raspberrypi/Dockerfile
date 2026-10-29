# Raspberry Pi 镜像端到端测试：官方 debian slim 容器 + armhf 架构 +
# Raspberry Pi apt 源指向镜像。keyring 引导：官方 archive.raspberrypi.org
# 的 raspberrypi-archive-keyring deb（超时回退镜像同源副本）；此后签名
# 校验与下载全程走镜像。只做 download（armhf 包体不装）。
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
