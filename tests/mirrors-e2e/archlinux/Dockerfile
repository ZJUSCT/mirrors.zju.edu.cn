# Arch Linux 镜像端到端测试：官方 base 容器 + pacman 源指向镜像站。
# 官方镜像自带 archlinux-keyring（包签名校验链）与 ca-certificates；
# 构建期补装一次 ca-certificates 以防基础镜像策略变化。
FROM archlinux:base
RUN pacman -Sy --noconfirm ca-certificates && pacman -Sc --noconfirm || true
COPY --chmod=755 e2e.sh /e2e.sh
ENTRYPOINT ["/e2e.sh"]
