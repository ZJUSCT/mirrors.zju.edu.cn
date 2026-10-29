# GNU 镜像端到端测试：alpine + gpg。keyring 从官方 ftp.gnu.org 引导，
# 镜像上的源码包用其 .sig 经 GNU 密钥环做真实签名校验，再解包冒烟。
FROM alpine:3.20
RUN apk add --no-cache curl gpg gpgv tar xz
COPY --chmod=755 e2e.sh /e2e.sh
ENTRYPOINT ["/e2e.sh"]
