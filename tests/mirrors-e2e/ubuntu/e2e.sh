#!/bin/sh
# Ubuntu 镜像端到端测试：apt 源改指镜像站 -> apt update（元数据刷新，
# Release/InRelease 签名校验）-> 安装一个包并验证可执行。基础镜像预装了
# file/diffutils 等，随机池避开；sl/jq 在 universe，故 Components 含 universe。
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
step() { echo; echo "==== [${1}] ${2} ===="; }

step 1 "镜像源配置"
# 从镜像自带 sources 提取 suite，重写为镜像站（保持签名校验链）
SRC=$(ls /etc/apt/sources.list.d/*.sources 2>/dev/null | head -1)
[ -z "$SRC" ] && SRC=/etc/apt/sources.list
SUITE=$(sed -n 's/^Suites: //p' "$SRC" | head -1 | awk '{print $1}')
[ -z "$SUITE" ] && SUITE=$(sed -n 's/^deb .* \/ubuntu *//p' "$SRC" | head -1 | awk '{print $1}')
echo "suite=$SUITE mirror=$MIRROR_HOST"
cat > /etc/apt/sources.list <<EOF
deb http://$MIRROR_HOST/ubuntu $SUITE main universe
deb http://$MIRROR_HOST/ubuntu $SUITE-updates main universe
deb http://$MIRROR_HOST/ubuntu $SUITE-security main universe
EOF
rm -f /etc/apt/sources.list.d/*.sources
cat /etc/apt/sources.list

step 2 "apt-get update（Release/InRelease 签名校验走镜像）"
apt-get update -o Acquire::Retries=2

step 3 "apt-get install"
if [ -z "${PKG:-}" ]; then
    PKG=$(shuf -e sl tree jq hello -n1)
fi
echo "本次安装：$PKG"
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "$PKG"

step 4 "可执行冒烟"
case "$PKG" in
    sl)     /usr/games/sl --help 2>&1 | head -1 || true ;;
    hello)  hello | head -1 ;;
    *)      "$PKG" --version 2>/dev/null | head -1 ;;
esac

echo
echo "==== E2E PASS（apt update/install 全程经镜像完成） ===="
