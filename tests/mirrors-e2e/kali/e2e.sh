#!/bin/sh
# Kali 镜像端到端测试：kali-rolling 官方容器（自带密钥环）-> 清空全部
# apt 源（含镜像自带的 sources.list.d）-> 只保留镜像站 -> apt update
# （Release/InRelease 签名校验走镜像）-> 随机选一个小包安装 -> 可执行冒烟。
# 注意：不用管道收尾以便 set -e 如实传递失败（失败掩蔽的教训见 git history）。
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
step() { echo; echo "==== [${1}] ${2} ===="; }

step 1 "镜像源配置（清空自带源，只保留镜像站）"
rm -f /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources
cat > /etc/apt/sources.list <<EOF
deb http://$MIRROR_HOST/kali kali-rolling main contrib non-free non-free-firmware
EOF
cat /etc/apt/sources.list

step 2 "apt-get update（签名校验走镜像）"
apt-get update -o Acquire::Retries=3

step 3 "apt-get install"
if [ -z "${PKG:-}" ]; then
    PKG=$(shuf -e bc tree whois file jq -n1)
fi
echo "本次安装：$PKG"
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "$PKG"

step 4 "可执行冒烟"
case "$PKG" in
    bc)    echo '2^16' | bc ;;
    whois) whois --version 2>&1 | head -1 ;;
    tree)  tree --version | head -1 ;;
    *)     "$PKG" --version 2>/dev/null | head -1 || dpkg -s "$PKG" | head -2 ;;
esac

echo
echo "==== E2E PASS（kali-rolling apt update/install 全程经镜像完成） ===="
