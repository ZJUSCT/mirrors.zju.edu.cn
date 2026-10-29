# CentOS Stream 镜像端到端测试：官方 stream9 容器 + dnf 源指向镜像站。
# 现代基础镜像自带完整 CA，无需补链。
FROM quay.io/centos/centos:stream9
COPY --chmod=755 e2e.sh /e2e.sh
ENTRYPOINT ["/e2e.sh"]
