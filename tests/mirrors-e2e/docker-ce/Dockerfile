# Docker CE 镜像端到端测试：官方 stable-slim 容器 + docker apt 源指向镜像。
# GPG key 引导自官方 download.docker.com（与 docker-ce 官方安装文档一致，
# 避免从镜像自身取 key 的循环信任）；此后 Release/包签名校验与下载全程走镜像。
# debian 基础镜像不带 ca-certificates，拷入 CA bundle 以验证官方上游的 HTTPS 连接。
FROM python:3.12-slim AS ca
FROM debian:stable-slim
COPY --from=ca /etc/ssl/certs /etc/ssl/certs
RUN mkdir -p /usr/lib/ssl \
    && ln -s /etc/ssl/certs /usr/lib/ssl/certs \
    && ln -s /etc/ssl/certs/ca-certificates.crt /usr/lib/ssl/cert.pem
RUN apt-get update && apt-get install -y --no-install-recommends curl gnupg \
    && rm -rf /var/lib/apt/lists/*
COPY --chmod=755 e2e.sh /e2e.sh
ENTRYPOINT ["/e2e.sh"]
