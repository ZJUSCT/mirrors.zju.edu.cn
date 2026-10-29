# Termux 镜像端到端测试：结构验证（alpine+curl）。termux 包体为 Android
# bionic 链接，无法在 Linux 安装执行；密钥环属 Android 生态同样不可用，
# 完整性以 Release 内哈希对账保证：Packages 索引经 Release 校验 -> 任选
# 小包经 Packages 内 SHA256 对账（等价 msys2 测试语义）。
FROM alpine:3.20
RUN apk add --no-cache curl
COPY --chmod=755 e2e.sh /e2e.sh
ENTRYPOINT ["/e2e.sh"]
