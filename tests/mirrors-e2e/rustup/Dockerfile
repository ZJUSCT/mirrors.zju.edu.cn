# Rustup 镜像端到端测试：官方 debian slim 容器。rustup-init 引导自官方
# static.rust-lang.org（sha256 校验，避免循环信任），随后 RUSTUP_DIST_SERVER
# 指向镜像站，工具链组件全部经镜像下载。debian 基础镜像不带
# ca-certificates，拷入 CA bundle 以验证官方上游的 HTTPS 连接。
FROM python:3.12-slim AS ca
FROM debian:stable-slim
COPY --from=ca /etc/ssl/certs /etc/ssl/certs
RUN mkdir -p /usr/lib/ssl \
    && ln -s /etc/ssl/certs /usr/lib/ssl/certs \
    && ln -s /etc/ssl/certs/ca-certificates.crt /usr/lib/ssl/cert.pem
RUN apt-get update && apt-get install -y --no-install-recommends curl gcc libc6-dev \
    && rm -rf /var/lib/apt/lists/*
COPY --chmod=755 e2e.sh /e2e.sh
ENTRYPOINT ["/e2e.sh"]
