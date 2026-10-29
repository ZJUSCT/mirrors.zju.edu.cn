# Deepin CD 镜像端到端测试：结构验证。ISO 体积数 GB，无法在测试中下载
# 全量哈希校验；校验发布目录的标志性工件（版本目录、SHA256SUMS、ISO 的
# Content-Length 与目录列表/清单一致）。
FROM alpine:3.20
RUN apk add --no-cache curl
COPY --chmod=755 e2e.sh /e2e.sh
ENTRYPOINT ["/e2e.sh"]
