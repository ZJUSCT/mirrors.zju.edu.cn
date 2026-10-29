# Manjaro 镜像端到端测试：官方 archlinux base 容器（pacman 与 manjaro 仓库
# 格式同源）。manjaro 包基于自研工具链，跨发行版安装不可靠，构建期仅从官方
# arch 仓库预置 ca-certificates / zstd / tar，运行期流量全部走镜像站。
FROM archlinux:base
RUN pacman -Sy --noconfirm ca-certificates zstd tar && pacman -Sc --noconfirm || true
COPY --chmod=755 e2e.sh /e2e.sh
ENTRYPOINT ["/e2e.sh"]
