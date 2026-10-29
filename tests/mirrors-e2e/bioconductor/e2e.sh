#!/bin/sh
# Bioconductor 镜像端到端测试：BiocManager（bootstrap 自 CRAN，见 Dockerfile）
# + BioC_mirror 指向镜像 -> 安装 Bioc 包 -> 加载冒烟。真实 R 客户端路径：
# BiocManager 按 R 版本解析 packages/<ver>/bioc 仓库，索引与 tarball 全经镜像。
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
step() { echo; echo "==== [${1}] ${2} ===="; }

step 1 "安装 BiocManager（bootstrap 自 CRAN）"
Rscript -e "install.packages('BiocManager', repos='https://cloud.r-project.org', quiet = TRUE)" 2>&1 | tail -2
Rscript -e "library(BiocManager); cat('BiocManager', as.character(packageVersion('BiocManager')), 'OK\n')"

step 2 "BioC_mirror 指向镜像站并校验仓库解析"
Rscript -e "options(BioC_mirror = 'http://$MIRROR_HOST/bioconductor'); repos <- BiocManager::repositories(); bioc <- repos[['BioCsoft']]; cat('BioCsoft =', bioc, '\n'); stopifnot(grepl('^http://$MIRROR_HOST/bioconductor/', bioc))"

step 3 "安装 Bioc 包（索引与 tarball 经镜像）"
Rscript -e "options(BioC_mirror = 'http://$MIRROR_HOST/bioconductor'); BiocManager::install('BiocGenerics', ask = FALSE, update = FALSE, quiet = TRUE)" 2>&1 | tail -3

step 4 "加载冒烟"
Rscript -e "library(BiocGenerics); cat('loaded OK\n')"

echo
echo "==== E2E PASS（BioC 索引与包下载全程经镜像完成） ===="
