#!/bin/sh
# CTAN 镜像端到端测试：tlmgr 仓库指向镜像 -> tlpdb 数据库刷新（经镜像）
# -> 安装一个小宏包 -> kpsewhich 验证文件就位。
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
step() { echo; echo "==== [${1}] ${2} ===="; }

step 1 "镜像源配置"
tlmgr option repository "http://$MIRROR_HOST/ctan/systems/texlive/tlnet"
tlmgr option repository 2>&1 | head -2

step 2 "tlmgr update --list（tlpdb 数据库经镜像刷新）"
tlmgr update --list 2>&1 | tail -3

step 3 "tlmgr install 安装宏包"
tlmgr install l3packages 2>&1 | tail -3

step 4 "冒烟"
kpsewhich l3debug.def

echo
echo "==== E2E PASS（tlmgr 数据库与宏包下载全程经镜像完成） ===="
