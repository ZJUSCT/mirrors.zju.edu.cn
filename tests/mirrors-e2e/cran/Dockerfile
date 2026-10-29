# CRAN 镜像端到端测试：官方 R 容器 + install.packages 经镜像安装包。
# repos 指向镜像的 CRAN 根（contrib 路径按 R 版本自动拼接），索引
#（PACKAGES[.gz/.rds]）与 tarball 下载、依赖解析全程经镜像。
FROM r-base:latest
COPY --chmod=755 e2e.sh /e2e.sh
CMD ["/e2e.sh"]
