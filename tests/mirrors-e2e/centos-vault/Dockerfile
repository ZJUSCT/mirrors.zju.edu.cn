# CentOS Vault 镜像端到端测试：官方 centos:7 容器 + yum 源指向镜像站的
# vault 树（7.9.2009 为 CentOS 7 最终版）。centos:7 已 EOL、原生源
# mirror.centos.org 已退役，本测试同时验证镜像对遗留系统的服务能力。
# 使用 HTTP 访问镜像，保留基础镜像原有的 CA 环境。
FROM centos:7
COPY --chmod=755 e2e.sh /e2e.sh
ENTRYPOINT ["/e2e.sh"]
