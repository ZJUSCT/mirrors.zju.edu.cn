# Gentoo 镜像端到端测试：alpine + wget 复刻 emerge-webrsync 的核心语义
# ——下载 portage 快照并用随附 md5sum 校验（快照由 Gentoo 基础设施签名
# 生成，md5sum 文件与 tarball 同源）。完整 emerge 链路需要 stage3 + gpg
# 环境，过重；快照下载+校验已是镜像侧可验证的最真实路径。
FROM alpine:3.20
RUN apk add -q --no-cache bash wget coreutils >/dev/null
COPY --chmod=755 e2e.sh /e2e.sh
ENTRYPOINT ["/e2e.sh"]
