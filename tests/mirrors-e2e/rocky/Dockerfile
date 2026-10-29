# Rocky Linux 镜像端到端测试：官方 9 容器 + dnf 源指向镜像。
# 容器内置 Rocky GPG key，repomd.xml/包签名校验链完整走镜像。
FROM rockylinux:9
COPY --chmod=755 e2e.sh /e2e.sh
ENTRYPOINT ["/e2e.sh"]
