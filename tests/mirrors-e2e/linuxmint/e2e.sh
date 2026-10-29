#!/bin/sh
# Linux Mint 镜像端到端测试：官方 linuxmint-keyring 包引导（取自官方
# packages.linuxmint.com，deb 内含密钥环）-> apt 源指向镜像（noble 系
# codename：zena/zara/xia/wilma 取第一个存在的）-> apt update（签名校验
# 走镜像）-> apt-get download 一个 Mint 包并冒烟。
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
BASE="http://$MIRROR_HOST/linuxmint"
step() { echo; echo "==== [${1}] ${2} ===="; }

step 1 "keyring 引导（官方 linuxmint-keyring deb，超时回退镜像同源副本）"
# 官方源优先；packages.linuxmint.com 跨境常超时，回退镜像副本（同一文件）
install -d /tmp
if curl -fsSL --max-time 60 \
    "https://packages.linuxmint.com/pool/main/l/linuxmint-keyring/linuxmint-keyring_2025.1_all.deb" \
    -o /tmp/keyring.deb 2>/dev/null; then
    echo "keyring 来源：官方 packages.linuxmint.com"
else
    echo "官方源超时，回退镜像副本（同源文件）"
    FN=$(curl -fsSL --max-time 30 "$BASE/pool/main/l/linuxmint-keyring/" | \
        grep -oE 'linuxmint-keyring_[0-9a-zA-Z.~_-]+_all\.deb' | sort -u | tail -1)
    [ -n "$FN" ] || { echo "FAIL: cannot locate keyring deb"; exit 1; }
    curl -fsSL --max-time 60 "$BASE/pool/main/l/linuxmint-keyring/$FN" -o /tmp/keyring.deb
fi
dpkg -i /tmp/keyring.deb
# deb 自带的是 ASCII 盔甲格式（且含多块），signed-by 需要 dearmor 后的二进制 keyring
gpg --dearmor < /usr/share/keyrings/linuxmint-keyring.gpg > /usr/share/keyrings/linuxmint-keyring-bin.gpg
ls -l /usr/share/keyrings/linuxmint-keyring-bin.gpg

step 2 "解析 codename 并配置 apt 源指向镜像"
CODENAME=""
for c in zena zara xia wilma; do
    if curl -fsSL --max-time 20 "$BASE/dists/$c/Release" -o /dev/null; then
        CODENAME=$c
        break
    fi
done
[ -n "$CODENAME" ] || { echo "FAIL: no noble-based mint codename found"; exit 1; }
echo "codename=$CODENAME"
# deb 自带 keyring 为 ASCII 盔甲多块格式，dearmor 成二进制供 signed-by 使用
install -d -m 0755 /etc/apt/keyrings
gpg --dearmor < /usr/share/keyrings/linuxmint-keyring.gpg > /etc/apt/keyrings/linuxmint-bin.gpg
cat > /etc/apt/sources.list.d/mint.list <<EOF
deb [signed-by=/etc/apt/keyrings/linuxmint-bin.gpg] $BASE $CODENAME main upstream import backport
EOF
cat /etc/apt/sources.list.d/mint.list

step 3 "apt-get update（签名校验走镜像）"
# 移除 ubuntu 基础源，只测 mint 仓库（基础源与本测试无关）
rm -f /etc/apt/sources.list.d/ubuntu.sources /etc/apt/sources.list
# APT::Sandbox::User=root：docker 内 _apt 用户创建 apt 临时文件失败会误报
# "repository is not signed"，测试容器内禁用沙箱（真机无需）
apt-get update -o Acquire::Retries=2 -o APT::Sandbox::User=root

step 4 "apt-get download 一个 Mint 包"
WORK=$(mktemp -d)
cd "$WORK"
PKG=$(apt-cache search --names-only '^mint-' 2>/dev/null | awk '{print $1}' | grep -v meta | head -1)
[ -n "$PKG" ] || PKG=mint-translations
echo "本次下载：$PKG"
apt-get download "$PKG"
ls -l ./*.deb

step 5 "包元数据冒烟"
dpkg-deb -f ./*.deb Package | head -1

rm -rf "$WORK"
echo
echo "==== E2E PASS（Mint apt 仓库索引与包下载全程经镜像完成） ===="
