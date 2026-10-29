# Mozilla apt 镜像端到端测试：官方 debian slim 容器 + Mozilla apt 源指向
# 镜像。GPG key 从官方 packages.mozilla.org 引导（repo-signing-key.gpg，
# 与 Mozilla 官方安装文档一致）；此后 Release/包签名校验与下载全程走镜像。
# 只做 download（firefox 包体 ~90MB、依赖重，安装冒烟意义有限）。
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
