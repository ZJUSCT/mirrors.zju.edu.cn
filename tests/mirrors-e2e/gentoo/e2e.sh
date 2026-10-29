#!/bin/sh
# Gentoo 镜像端到端测试：定位最新 portage 快照 -> 下载 tarball 与 md5sum
# （均经镜像）-> md5 校验 -> tar 结构冒烟。等价 emerge-webrsync 的镜像侧
# 语义。
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
step() { echo; echo "==== [${1}] ${2} ===="; }
BASE="http://$MIRROR_HOST/gentoo"
WORK=$(mktemp -d)
cd "$WORK"

step 1 "镜像源配置"
echo "mirror=$BASE"

step 2 "获取最新快照名（snapshots 目录列表经镜像）"
SNAP=$(wget -qO- "$BASE/snapshots/" | grep -oE "\"name\":\"gentoo-[0-9]+\.tar\.xz\"" | tr -d '"' | sed 's/name://' | sort -u | tail -1)
[ -n "$SNAP" ] || { echo "cannot resolve snapshot name"; exit 1; }
echo "snapshot: $SNAP"

step 3 "下载 tarball 与 md5sum（经镜像）"
wget -q "$BASE/snapshots/$SNAP"
wget -q "$BASE/snapshots/$SNAP.md5sum"
ls -l "$SNAP"

step 4 "md5 校验"
md5sum -c "$SNAP.md5sum"

step 5 "tar 结构冒烟"
tar -tf "$SNAP" | head -3

echo
echo "==== E2E PASS（portage 快照下载与校验全程经镜像完成） ===="
