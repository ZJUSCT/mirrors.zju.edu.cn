# Packman 镜像端到端测试：官方 openSUSE Tumbleweed 容器 + packman 源指向
# 镜像。--gpg-auto-import-keys 从 packman 仓库元数据引入其签名 key
# （packman 官方用户文档的标准做法），refresh 完成仓库元数据签名校验链，
# 随后安装一个 packman 多媒体小包。
FROM opensuse/tumbleweed
RUN zypper -n install curl
COPY --chmod=755 e2e.sh /e2e.sh
ENTRYPOINT ["/e2e.sh"]
