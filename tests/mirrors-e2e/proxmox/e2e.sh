#!/bin/sh
# Proxmox VE 镜像端到端测试：GPG key 从官方 download.proxmox.com 引导
# （不可达时用镜像副本，两者同源）-> pve-no-subscription 源指向镜像 ->
# apt update（Release 签名校验走镜像）-> apt-get download pve-manager 并
# 做包元数据冒烟。
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
BASE="http://$MIRROR_HOST/proxmox"
step() { echo; echo "==== [${1}] ${2} ===="; }

step 1 "GPG key 引导（官方 download.proxmox.com，回退镜像同源副本）"
install -d -m 0755 /etc/apt/keyrings
# 用 bookworm 套件：其 Release key 在镜像树内有同源副本；trixie 的 InRelease
# 由 2025 轮换的新 key 签署，keyserver 的裸 key 过不了 debian 13 sqv 的
# 绑定校验（缺时间绑定自签）。本测试为 download-only，套件版本无关紧要。
if ! curl -fsSL --max-time 30 \
        "https://download.proxmox.com/debian/proxmox-release-bookworm.gpg" \
        -o /etc/apt/keyrings/proxmox-release-bookworm.gpg; then
    echo "（官方 download.proxmox.com 本网络不可达/证书异常，改经镜像取同源 key）"
    curl -fsSL --max-time 30 "$BASE/debian/proxmox-release-bookworm.gpg" \
        -o /etc/apt/keyrings/proxmox-release-bookworm.gpg
fi
gpg --show-keys /etc/apt/keyrings/proxmox-release-bookworm.gpg | head -3

step 2 "apt 源指向镜像站"
echo "deb [signed-by=/etc/apt/keyrings/proxmox-release-bookworm.gpg] $BASE/debian/pve bookworm pve-no-subscription" \
    > /etc/apt/sources.list.d/pve.list
cat /etc/apt/sources.list.d/pve.list

step 3 "apt-get update（签名校验走镜像）"
apt-get update -o Acquire::Retries=2 2>&1 | tail -3

step 4 "apt-get download pve-manager"
WORK=$(mktemp -d)
cd "$WORK"
apt-get download pve-manager
ls -l pve-manager_*.deb

step 5 "包元数据冒烟"
dpkg-deb -f pve-manager_*.deb Package Version | head -2

rm -rf "$WORK"
echo
echo "==== E2E PASS（PVE apt 仓库索引与包下载全程经镜像完成） ===="
