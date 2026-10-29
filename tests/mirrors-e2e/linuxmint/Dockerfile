# Linux Mint 镜像端到端测试：官方 ubuntu:24.04 容器（Mint 22.x 基于 noble）
# + Mint apt 源指向镜像。keyring 引导：从官方 packages.linuxmint.com 安装
# linuxmint-keyring 包（含 /usr/share/keyrings/linuxmint-keyring.gpg），
# 与 Mint 官方文档的接入方式一致；此后签名校验与下载全程走镜像。
FROM ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends curl gnupg ca-certificates dpkg \
    && rm -rf /var/lib/apt/lists/*
COPY --chmod=755 e2e.sh /e2e.sh
ENTRYPOINT ["/e2e.sh"]
