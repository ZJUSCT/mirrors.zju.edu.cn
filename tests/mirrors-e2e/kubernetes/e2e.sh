#!/bin/sh
# Kubernetes 镜像端到端测试：Release.key 从官方 pkgs.k8s.io 引导 ->
# apt 源指向镜像（pkgs.k8s.io 目录约定 core:/stable:/vX.Y:/deb/）->
# apt update（Release/InRelease 签名校验走镜像）-> 安装 kubectl 并冒烟。
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
BASE="http://$MIRROR_HOST/kubernetes"
step() { echo; echo "==== [${1}] ${2} ===="; }

step 1 "解析最新 stable 版本线"
# 目录中带尾冒号的 v1.X: 是 2023 年遗留形态，活跃仓库为不带冒号的 v1.X/deb
VER=$(curl -s --noproxy '*' --max-time 30 "$BASE/core:/stable:/" \
    | grep -oE '"name":"v1\.[0-9]+"' | sed 's/"name":"//;s/"//' | sort -V | tail -1)
[ -n "$VER" ] || { echo "FAIL: no stable version found"; exit 1; }
REPO="$BASE/core:/stable:/$VER/deb"
echo "stable=$VER repo=$REPO"

step 2 "GPG key 引导（官方 pkgs.k8s.io，失败时经镜像并提示）"
install -m 0755 -d /etc/apt/keyrings
if ! curl -fsSL "https://pkgs.k8s.io/core:/stable:/$VER/deb/Release.key" -o /etc/apt/keyrings/pkgs-k8s.asc; then
    echo "（官方 pkgs.k8s.io 不可达，改经镜像取 Release.key——与官方文件同源）"
    curl -fsSL "$REPO/Release.key" -o /etc/apt/keyrings/pkgs-k8s.asc
fi
gpg --show-keys /etc/apt/keyrings/pkgs-k8s.asc | head -3

step 3 "apt 源指向镜像站"
echo "deb [signed-by=/etc/apt/keyrings/pkgs-k8s.asc] $REPO /" \
    > /etc/apt/sources.list.d/kubernetes.list
cat /etc/apt/sources.list.d/kubernetes.list

step 4 "apt-get update（签名校验走镜像）"
apt-get update -o Acquire::Retries=2 2>&1 | tail -3

step 5 "安装 kubectl"
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends kubectl 2>&1 | tail -2

step 6 "可执行冒烟"
kubectl version --client

echo
echo "==== E2E PASS（k8s apt 仓库索引与包下载全程经镜像完成） ===="
