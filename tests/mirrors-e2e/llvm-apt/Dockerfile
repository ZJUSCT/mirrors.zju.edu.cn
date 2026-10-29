# LLVM apt 镜像端到端测试：官方 debian slim 容器 + LLVM apt 源指向镜像。
# GPG key 从官方 apt.llvm.org 引导（llvm-snapshot.gpg.key，与官方安装文档
# 一致，避免循环信任）；此后 Release/包签名校验与下载全程走镜像。
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
