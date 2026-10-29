#!/bin/sh
# anthon（AOSC OS）镜像端到端测试：oma 源改指镜像站 -> oma refresh（元数据
# 刷新）-> 安装一个包并验证可执行。
# 上游 repo.aosc.io/anthon/ 与镜像站 /anthon/ 路径一一对应。
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
SRC=/etc/apt/sources.list

step() { echo; echo "==== [${1}] ${2} ===="; }

step 1 "镜像源配置"
sed -i "s#https://repo.aosc.io#http://$MIRROR_HOST#" "$SRC"
cat "$SRC"

step 2 "oma refresh（元数据刷新走镜像）"
oma refresh

step 3 "oma install"
if [ -z "${PKG:-}" ]; then
    # AOSC 容器自带 tree/jq/bc/cpio 等常见工具（oma 判定“已安装”而跳过
    # 下载），故选容器里肯定没有的小包
    PKG=$(shuf -e cmatrix neofetch htop sl -n1)
fi
echo "本次安装：$PKG"
oma install -y "$PKG"

step 4 "可执行冒烟"
command -v "$PKG" >/dev/null && "$PKG" --version 2>/dev/null | head -1

echo
echo "==== E2E PASS（oma refresh/install 全程经镜像完成） ===="
