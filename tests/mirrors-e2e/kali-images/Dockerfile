# Kali Images 镜像端到端测试：结构验证。ISO 数 GB 不做全量下载；校验
# kali-weekly 目录的 SHA256SUMS 覆盖与 ISO 的 Content-Length 对账。
FROM alpine:3.20
RUN apk add --no-cache curl
COPY --chmod=755 e2e.sh /e2e.sh
ENTRYPOINT ["/e2e.sh"]
