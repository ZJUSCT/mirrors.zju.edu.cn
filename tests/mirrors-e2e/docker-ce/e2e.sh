#!/bin/sh
# Docker CE 镜像端到端测试：GPG key 从官方 download.docker.com 引导 ->
# apt 源指向镜像 -> apt update（Release/InRelease 签名校验走镜像）->
# 安装 docker-ce-cli 并冒烟。
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
step() { echo; echo "==== [${1}] ${2} ===="; }

step 1 "GPG key 引导（官方 download.docker.com）"
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
apt-key fingerprint 0EBFCD88 2>/dev/null | head -2 || gpg --show-keys --with-fingerprint /etc/apt/keyrings/docker.asc | head -4

step 2 "apt 源指向镜像站"
CODENAME=$(. /etc/os-release && echo "${VERSION_CODENAME:-bookworm}")
echo "deb [signed-by=/etc/apt/keyrings/docker.asc] http://$MIRROR_HOST/docker-ce/linux/debian $CODENAME stable" \
    > /etc/apt/sources.list.d/docker.list
cat /etc/apt/sources.list.d/docker.list

step 3 "apt-get update（签名校验走镜像）"
apt-get update -o Acquire::Retries=2 2>&1 | tail -3

step 4 "安装 docker-ce-cli"
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends docker-ce-cli 2>&1 | tail -2

step 5 "可执行冒烟"
docker --version

echo
echo "==== E2E PASS（docker apt 仓库索引与包下载全程经镜像完成） ===="
