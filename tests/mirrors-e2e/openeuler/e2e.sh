#!/bin/sh
# openEuler 镜像端到端测试：dnf repo 改指镜像站 -> dnf makecache（元数据
# 刷新，GPG 签名校验走镜像）-> 安装一个包并验证可执行。
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
VER="${VER:-24.03-LTS-SP4}"
step() { echo; echo "==== [${1}] ${2} ===="; }

step 1 "镜像源配置"
cat > /etc/yum.repos.d/openeuler.repo <<EOF
[OS]
name=OS
baseurl=http://${MIRROR_HOST}/openeuler/openEuler-${VER}/OS/\$basearch/
enabled=1
gpgcheck=1
gpgkey=http://${MIRROR_HOST}/openeuler/openEuler-${VER}/OS/\$basearch/RPM-GPG-KEY-openEuler
EOF
cat /etc/yum.repos.d/openeuler.repo
rm -f /etc/yum.repos.d/openEuler.repo

step 2 "dnf makecache（repodata/GPG 校验走镜像）"
dnf makecache --refresh -y --setopt=timeout=30

step 3 "dnf install"
if [ -z "${PKG:-}" ]; then
    PKG=$(shuf -e tree jq bc wget -n1)
fi
echo "本次安装：$PKG"
dnf install -y "$PKG"

step 4 "可执行冒烟"
case "$PKG" in
    tree)  tree --version 2>&1 | head -1 ;;
    jq)    jq --version ;;
    bc)    echo '2^10' | bc ;;
    wget)  wget --version 2>&1 | head -1 ;;
esac

echo
echo "==== E2E PASS（dnf makecache/install 全程经镜像完成） ===="
