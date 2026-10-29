# CTAN 镜像端到端测试：官方 TeX Live 容器 + tlmgr 经镜像安装/更新宏包。
# tlmgr option repository 指向镜像的 tlnet 路径后，update --list 拉远端
# 数据库（tlpkg/texlive.tlpdb），install 下载真实包。
FROM texlive/texlive:latest
COPY --chmod=755 e2e.sh /e2e.sh
ENTRYPOINT ["/e2e.sh"]
