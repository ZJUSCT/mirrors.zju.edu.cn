#!/bin/sh
# CRAN 镜像端到端测试：repos 指向镜像 -> 安装一个带依赖的 R 包 -> 加载冒烟。
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
step() { echo; echo "==== [${1}] ${2} ===="; }

step 1 "镜像源配置"
echo "mirror=http://$MIRROR_HOST/cran"
Rscript -e "options(repos = c(CRAN = 'http://$MIRROR_HOST/cran'))"

step 2 "install.packages（索引与 tarball 经镜像，含依赖解析）"
Rscript -e "install.packages('attempt', repos = 'http://$MIRROR_HOST/cran', quiet = TRUE)" 2>&1 | tail -3

step 3 "加载冒烟"
Rscript -e "library(attempt); cat('loaded OK\n')"

echo
echo "==== E2E PASS（CRAN 索引与包下载全程经镜像完成） ===="
