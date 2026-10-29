#!/bin/sh
# Packman 镜像端到端测试：zypper 添加 packman Tumbleweed 源（指向镜像）->
# --gpg-auto-import-keys refresh（packman key 随仓库元数据引入，repomd
# 签名校验走镜像）-> 安装一个 packman 小包（lame，依赖由 OSS 仓满足）->
# 可执行冒烟。
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
step() { echo; echo "==== [${1}] ${2} ===="; }

step 1 "添加 packman 源（指向镜像站）"
zypper ar -f -n packman "http://$MIRROR_HOST/packman/suse/openSUSE_Tumbleweed/" packman

step 2 "refresh（元数据签名校验走镜像）"
zypper --gpg-auto-import-keys -n refresh -r packman 2>&1 | tail -4

step 3 "安装 packman 小包（lame）"
zypper -n --gpg-auto-import-keys install --from packman lame 2>&1 | tail -4

step 4 "可执行冒烟"
lame --version 2>&1 | head -1
rpm -q lame

echo
echo "==== E2E PASS（packman 元数据与包安装全程经镜像完成） ===="
