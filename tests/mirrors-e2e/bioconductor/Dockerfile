# Bioconductor 镜像端到端测试：官方 r-base 容器 + BiocManager。
# BiocManager 本体来自 CRAN（bootstrap，staging 实例不含 cran 镜像）；
# 之后 BioC_mirror 指向镜像站，索引（PACKAGES[.gz/.rds]）与包 tarball
# 下载、依赖解析全程经镜像，与真实 R 用户的接入路径一致。
FROM r-base:latest
COPY --chmod=755 e2e.sh /e2e.sh
CMD ["/e2e.sh"]
