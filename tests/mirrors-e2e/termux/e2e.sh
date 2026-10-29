#!/bin/sh
# Termux 镜像端到端测试：结构验证（Android bionic 包体不可安装，密钥环
# 不可用，见 Dockerfile）。校验链：dists/stable/Release 内 SHA256 ->
# main/binary-aarch64/Packages.gz 对账 -> 从索引取小包的 Filename/SHA256 ->
# 全量下载对账。
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
BASE="http://$MIRROR_HOST/termux/apt/termux-main/dists/stable"
step() { echo; echo "==== [${1}] ${2} ===="; }
get() { curl -s --noproxy '*' --max-time 60 "$@"; }
WORK=$(mktemp -d)
cd "$WORK"

step 1 "Release 文件与 Packages 索引哈希"
get "$BASE/Release" -o Release
grep -q "^SHA256:" Release || { echo "FAIL: no SHA256 section"; exit 1; }
EXPECT=$(awk '/^SHA256:/{f=1; next} /^[A-Za-z]+:$/{f=0} f && / main\/binary-aarch64\/Packages$/ {print $1; exit}' Release)
[ -n "$EXPECT" ] || { echo "FAIL: Packages not in Release SHA256 section"; exit 1; }
echo "Release 记录的 Packages sha256: $EXPECT"

step 2 "下载 Packages 并校验"
get "$BASE/main/binary-aarch64/Packages" -o Packages
ACTUAL=$(sha256sum Packages | awk '{print $1}')
[ "$ACTUAL" = "$EXPECT" ] || { echo "FAIL: sha256 mismatch"; exit 1; }
echo "OK: Packages sha256 一致"

step 3 "从索引取小包（≤5MB）并对账"
PAIR=$(awk -F': ' '$1=="Filename"{f=$2} $1=="SHA256"{h=$2} $1=="Size"{s=$2} /^$/{if (f!="" && s+0>0 && s+0<5242880) {print f, h, s; exit} f=""; h=""; s=""}' Packages)
[ -n "$PAIR" ] || PAIR=$(awk -F': ' '$1=="Filename"{f=$2} $1=="SHA256"{h=$2} $1=="Size"{s=$2} END{if (s+0<5242880) print f, h, s}' Packages)
FN=$(echo "$PAIR" | awk '{print $1}')
EXPECTH=$(echo "$PAIR" | awk '{print $2}')
SZ=$(echo "$PAIR" | awk '{print $3}')
[ -n "$FN" ] && [ -n "$EXPECTH" ] || { echo "FAIL: cannot parse Packages"; exit 1; }
echo "包：$FN (Size $SZ)"

step 4 "下载包体并 sha256 对账"
# Filename 相对 termux-main 仓库根（$BASE/../..）
REPO_ROOT="${BASE%/*/*}"
get "$REPO_ROOT/$FN" -o pkg.deb
[ -s pkg.deb ] || { echo "FAIL: package download empty"; exit 1; }
ACTUALH=$(sha256sum pkg.deb | awk '{print $1}')
[ "$ACTUALH" = "$EXPECTH" ] || { echo "FAIL: sha256 mismatch ($ACTUALH != $EXPECTH)"; exit 1; }
echo "OK: 包体 sha256 与索引一致"

rm -rf "$WORK"
echo
echo "==== E2E PASS（Release->Packages->包体 哈希链对账完成） ===="
