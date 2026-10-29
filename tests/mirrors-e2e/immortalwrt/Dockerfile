# ImmortalWrt 镜像端到端测试：结构验证 + 小镜像全量 sha256 校验。
# 选最新 release 下第一个 targets/<t>/<s>/，取 ≤10MB 的 img.gz 全量下载，
# 与官方 sha256sums 对账（OpenWrt 系 sha256sums 覆盖目录内全部工件）。
FROM alpine:3.20
RUN apk add --no-cache curl
COPY --chmod=755 e2e.sh /e2e.sh
ENTRYPOINT ["/e2e.sh"]
