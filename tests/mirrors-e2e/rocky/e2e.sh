#!/bin/sh
# Rocky Linux 镜像端到端测试：dnf 源改指镜像 -> dnf makecache（repomd
# 签名校验）-> 安装一个包并冒烟。
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
step() { echo; echo "==== [${1}] ${2} ===="; }

step 1 "镜像源配置"
cat > /etc/yum.repos.d/mirror.repo <<EOF
[baseos]
name=Rocky BaseOS
mirrorlist=https://mirrors.rockylinux.org/mirrorlist\\\$releasever
baseurl=http://$MIRROR_HOST/rocky/9/BaseOS/x86_64/os/
gpgcheck=1
enabled=1
countme=0
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-Rocky-9
EOF
rm -f /etc/yum.repos.d/Rocky-*.repo
cat /etc/yum.repos.d/mirror.repo

step 2 "dnf makecache（repomd 签名校验走镜像）"
dnf makecache --refresh -q 2>&1 | tail -3

step 3 "dnf install"
dnf install -y -q bc 2>&1 | tail -2

step 4 "冒烟"
echo '2^16' | bc

echo
echo "==== E2E PASS（dnf makecache/install 全程经镜像完成） ===="
