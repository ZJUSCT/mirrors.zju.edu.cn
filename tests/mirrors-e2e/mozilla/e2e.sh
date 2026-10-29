#!/bin/sh
# Mozilla apt 镜像端到端测试：GPG key 从官方 packages.mozilla.org 引导 ->
# apt 源指向镜像（suite: apt）-> apt update（签名校验走镜像）->
# apt-get download firefox（下载亦经 apt 包签名校验）-> 包元数据冒烟。
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
step() { echo; echo "==== [${1}] ${2} ===="; }

step 1 "GPG key 引导（官方 packages.mozilla.org）"
install -d -m 0755 /etc/apt/keyrings
curl -fsSL https://packages.mozilla.org/apt/repo-signing-key.gpg -o /etc/apt/keyrings/mozilla.asc
gpg --show-keys /etc/apt/keyrings/mozilla.asc | head -3

step 2 "apt 源指向镜像站"
# 仓库 URL 为 /mozilla/apt，suite 名为 mozilla
echo "deb [signed-by=/etc/apt/keyrings/mozilla.asc] http://$MIRROR_HOST/mozilla/apt mozilla main" \
    > /etc/apt/sources.list.d/mozilla.list
cat /etc/apt/sources.list.d/mozilla.list

step 3 "apt-get update（签名校验走镜像）"
apt-get update -o Acquire::Retries=2 2>&1 | tail -3

step 4 "apt-get download firefox（下载经签名校验）"
WORK=$(mktemp -d)
cd "$WORK"
apt-get download firefox
ls -l firefox_*.deb

step 5 "包元数据冒烟"
dpkg-deb -f firefox_*.deb Package Version | head -2

rm -rf "$WORK"
echo
echo "==== E2E PASS（Mozilla apt 仓库索引与包下载全程经镜像完成） ===="
