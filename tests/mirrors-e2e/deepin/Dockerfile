# Deepin 镜像端到端测试：结构验证。deepin 无官方客户端容器（Docker Hub
# deepin org 仅有 2017 年的陈旧 deepin-core），apt 签名校验链缺信任锚点
# （deepin 归档密钥只存在于 deepin 系统内），故做元数据自洽性校验：
# Release 文件 -> Packages 索引 SHA256 -> 包本体 Content-Length 对账。
FROM alpine:3.20
RUN apk add --no-cache curl
COPY --chmod=755 e2e.sh /e2e.sh
ENTRYPOINT ["/e2e.sh"]
