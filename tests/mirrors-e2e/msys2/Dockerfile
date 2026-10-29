# MSYS2 镜像端到端测试：官方 archlinux base 容器（pacman 与 msys2 同源同格式）。
# msys2 包体为 Windows PE，无法在 Linux 安装执行，构建期仅从官方 arch 仓库
# 预置 ca-certificates / zstd / tar，运行期流量全部走镜像站。
FROM archlinux:base
RUN pacman -Sy --noconfirm ca-certificates zstd tar && pacman -Sc --noconfirm || true
COPY --chmod=755 e2e.sh /e2e.sh
ENTRYPOINT ["/e2e.sh"]
