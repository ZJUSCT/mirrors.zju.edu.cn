# Ubuntu 镜像端到端测试：官方 24.04 容器 + apt 源指向镜像站。
# 使用 HTTP，无需额外安装 CA；保留 ubuntu-archive-keyring 验证 Release 签名。
FROM ubuntu:24.04
COPY --chmod=755 e2e.sh /e2e.sh
ENTRYPOINT ["/e2e.sh"]
