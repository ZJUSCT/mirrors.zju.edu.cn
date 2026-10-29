# ELRepo 镜像端到端测试：官方 rockylinux:9 容器 + elrepo 仓库指向镜像。
# 引导顺序：先从镜像安装 elrepo-release RPM（--nogpgcheck 引导，其携带
# ELRepo GPG key），此后 repomd/包的签名校验即基于该 key 经镜像完成，
# 与真实用户的 elrepo 接入路径一致。
FROM rockylinux:9
COPY --chmod=755 e2e.sh /e2e.sh
ENTRYPOINT ["/e2e.sh"]
