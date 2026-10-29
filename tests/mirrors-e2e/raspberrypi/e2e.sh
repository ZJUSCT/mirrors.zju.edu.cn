#!/bin/sh
# Raspberry Pi 镜像端到端测试：raspberrypi-archive-keyring 引导（官方优先，
# 回退镜像同源副本）-> armhf 架构 + apt 源指向镜像 -> apt update（签名校验
# 走镜像）-> apt-get download 一个 armhf 包并校验架构元数据。
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
BASE="http://$MIRROR_HOST/raspberrypi"
step() { echo; echo "==== [${1}] ${2} ===="; }

step 1 "keyring 引导（官方优先，回退镜像同源副本）"
install -d -m 0755 /etc/apt/keyrings /tmp/work
cd /tmp/work
FN=""
for HOST in "https://archive.raspberrypi.org/debian" "$BASE"; do
    FN=$(curl -fsSL --max-time 30 "$HOST/pool/main/r/raspberrypi-archive-keyring/" 2>/dev/null | \
        grep -oE 'raspberrypi-archive-keyring_[0-9a-zA-Z.+~_-]+_all\.deb' | sort -u | tail -1) || true
    if [ -n "$FN" ] && curl -fsSL --max-time 60 "$HOST/pool/main/r/raspberrypi-archive-keyring/$FN" -o keyring.deb 2>/dev/null; then
        echo "keyring 来源：$HOST"
        break
    fi
done
[ -s keyring.deb ] || { echo "FAIL: cannot fetch keyring deb"; exit 1; }
dpkg -i keyring.deb
# 2025.1 版 keyring 安装到 /etc/apt/trusted.gpg.d/raspberrypi-archive.asc
KR=/etc/apt/trusted.gpg.d/raspberrypi-archive.asc
[ -s "$KR" ] || { echo "FAIL: keyring file missing"; exit 1; }

step 2 "apt 源指向镜像站（armhf）"
dpkg --add-architecture armhf
echo "deb [arch=armhf signed-by=$KR] $BASE bookworm main" \
    > /etc/apt/sources.list.d/rpi.list
cat /etc/apt/sources.list.d/rpi.list

step 3 "apt-get update（armhf 索引，签名校验走镜像）"
apt-get update -o Acquire::Retries=2 -o APT::Sandbox::User=root 2>&1 | tail -3

step 4 "apt-get download 一个 armhf 包"
cd /tmp/work
PKG=$(apt-cache search --names-only '^rpi-|^raspberrypi' 2>/dev/null | awk '{print $1}' | grep -vE 'bootloader|firmware|keyring' | head -1)
[ -n "$PKG" ] || PKG=rpi-eeprom
echo "本次下载：$PKG"
apt-get download "$PKG"
ls -l ./*.deb

step 5 "架构元数据冒烟"
ARCH=$(dpkg-deb -f "$PKG"_*.deb Architecture)
echo "$PKG architecture: $ARCH"
[ "$ARCH" = "armhf" ] || { echo "FAIL: expected armhf package"; exit 1; }

echo
echo "==== E2E PASS（Raspberry Pi apt 仓库索引与包下载全程经镜像完成） ===="
