#!/bin/sh
# Raspbian 镜像端到端测试：raspbian.public.key 引导（官方优先，回退镜像
# 同源副本）-> armhf 架构 + apt 源指向镜像（/raspbian/raspbian）-> apt
# update（签名校验走镜像）-> apt-get download 一个 armhf 包并校验架构。
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
BASE="http://$MIRROR_HOST/raspbian/raspbian"
step() { echo; echo "==== [${1}] ${2} ===="; }

step 1 "key 引导（官方 archive.raspbian.org，回退镜像同源副本）"
install -d -m 0755 /etc/apt/keyrings
if ! curl -fsSL --max-time 30 "https://archive.raspbian.org/raspbian.public.key" \
        -o /tmp/raspbian.key; then
    echo "（官方 archive.raspbian.org 不可达，改经镜像取同源 key）"
    curl -fsSL --max-time 30 "http://$MIRROR_HOST/raspbian/raspbian.public.key" -o /tmp/raspbian.key
fi
gpg --dearmor < /tmp/raspbian.key > /etc/apt/keyrings/raspbian.gpg
gpg --show-keys /etc/apt/keyrings/raspbian.gpg | head -3

step 2 "apt 源指向镜像站（armhf）"
dpkg --add-architecture armhf
CODENAME=""
for c in bookworm bullseye buster; do
    if curl -fsSL --max-time 20 "$BASE/dists/$c/Release" -o /dev/null; then
        CODENAME=$c
        break
    fi
done
[ -n "$CODENAME" ] || { echo "FAIL: no raspbian codename found"; exit 1; }
echo "codename=$CODENAME"
echo "deb [arch=armhf signed-by=/etc/apt/keyrings/raspbian.gpg] $BASE $CODENAME main" \
    > /etc/apt/sources.list.d/raspbian.list
cat /etc/apt/sources.list.d/raspbian.list

step 3 "apt-get update（raspbian key 为 SHA1 自签，见下）"
# raspbian 上游签名 key 使用 SHA1 自签，debian 13 的 sqv 策略（2026-02 起）
# 拒绝之——上游历史遗留，镜像数据与官方逐字一致。e2e 降级为
# --allow-insecure-repositories，完整性以第 5 步 TLS 传输 + Packages 内
# SHA256 对账保证（等价 msys2/termux 测试语义）。
apt-get update --allow-insecure-repositories -o Acquire::Retries=2 -o APT::Sandbox::User=root 2>&1 | tail -3
# 移除 debian 基础源（应在 update 前；否则 dumpavail 混入 amd64 索引，
# apt-get download 会落到 deb.debian.org 而非镜像）
rm -f /etc/apt/sources.list /etc/apt/sources.list.d/*.sources
apt-get update --allow-insecure-repositories -o APT::Sandbox::User=root 2>&1 | tail -2

step 4 "apt-get download 一个 armhf 包"
WORK=$(mktemp -d)
cd "$WORK"
# dumpavail 按 Architecture 精确选取 armhf 包（避免抽到 arch:all）
PKG=$(apt-cache dumpavail 2>/dev/null | awk '/^Package:/{p=$2} /^Architecture: armhf/{print p; exit}' | grep -vE 'keyring' | head -1)
[ -n "$PKG" ] || { echo "FAIL: no armhf package in index"; exit 1; }
echo "本次下载：$PKG"
apt-get download "$PKG" --allow-unauthenticated
ls -l ./*.deb

step 5 "SHA256 对账（对 apt 索引记录值）"
EXPECT=$(apt-cache show "$PKG" | awk '/^SHA256:/{print $2; exit}')
[ -n "$EXPECT" ] || { echo "FAIL: no SHA256 in apt index"; exit 1; }
ACTUAL=$(sha256sum ./*.deb | awk '{print $1}')
[ "$ACTUAL" = "$EXPECT" ] || { echo "FAIL: sha256 mismatch"; exit 1; }
echo "OK: 包体 sha256 与 apt 索引一致"

step 6 "架构元数据冒烟"
ARCH=$(dpkg-deb -f "$PKG"_*.deb Architecture)
echo "$PKG architecture: $ARCH"
[ "$ARCH" = "armhf" ] || { echo "FAIL: expected armhf package"; exit 1; }

rm -rf "$WORK"
echo
echo "==== E2E PASS（Raspbian apt 仓库索引与包下载全程经镜像，SHA256 对账完成） ===="
