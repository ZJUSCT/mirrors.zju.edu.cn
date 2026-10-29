# Qt 镜像端到端测试：alpine + wget 下载官方在线安装器（real asset）。
# Qt 无包管理器语义，安装器本身即客户端；校验尺寸与 ELF/脚本 magic。
# 官方发布树无伴随 .sha256 文件，完整性以传输成功 + 尺寸一致为准。
FROM alpine:3.20
RUN apk add -q --no-cache bash wget file >/dev/null
COPY --chmod=755 e2e.sh /e2e.sh
ENTRYPOINT ["/e2e.sh"]
