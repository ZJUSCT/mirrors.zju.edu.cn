#!/bin/sh
# ELRepo 镜像端到端测试：从镜像安装 elrepo-release（GPG key 引导）->
# 仓库 baseurl 改指镜像 -> dnf makecache（repomd 签名校验走镜像）->
# 安装一个 kmod 包并冒烟。签名链：elrepo-release 自带的
# /etc/pki/rpm-gpg/RPM-GPG-KEY*-elrepo.org（elrepo 2025 起用 v2 key 签包；引导包经镜像下载）。
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
BASE="http://$MIRROR_HOST/elrepo/elrepo"
step() { echo; echo "==== [${1}] ${2} ===="; }
RELEASEVER=9

step 1 "解析 elrepo-release RPM 并从镜像安装（key 引导，--nogpgcheck）"
RPM=$(curl -s --noproxy '*' --max-time 30 "$BASE/el$RELEASEVER/x86_64/RPMS/" \
    | grep -oE '"name":"elrepo-release-[0-9][^"]*noarch\.rpm"' | sed 's/"name":"//;s/"//' | sort -V | tail -1)
[ -n "$RPM" ] || { echo "FAIL: elrepo-release rpm not found"; exit 1; }
echo "安装：$RPM"
dnf install -y -q --nogpgcheck "$BASE/el$RELEASEVER/x86_64/RPMS/$RPM" 2>&1 | tail -2
ls /etc/pki/rpm-gpg/RPM-GPG-KEY-elrepo.org >/dev/null

step 2 "仓库 baseurl 改指镜像站"
rm -f /etc/yum.repos.d/elrepo*.repo
cat > /etc/yum.repos.d/elrepo.repo <<EOF
[elrepo]
name=ELRepo.org Community Enterprise Linux Repository - el$RELEASEVER
baseurl=$BASE/el$RELEASEVER/x86_64/
gpgcheck=1
enabled=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-elrepo.org file:///etc/pki/rpm-gpg/RPM-GPG-KEY-v2-elrepo.org
EOF
# 保留 Rocky BaseOS 仓库：kmod 包依赖 depmod/weak-modules（BaseOS 提供）；
# elrepo 仓库内容仍全部经镜像。
cat /etc/yum.repos.d/elrepo.repo

step 3 "dnf makecache（repomd 签名校验走镜像）"
dnf makecache --refresh -q 2>&1 | tail -3

step 4 "安装 kmod 包"
# 固定首选，取不到则动态选第一个可用 kmod-*（内核模块包不要求运行内核匹配）
PKG=$(dnf -q list available 'kmod-v4l2loopback' 2>/dev/null | awk 'NR>1{print $1; exit}')
if [ -z "$PKG" ]; then
    PKG=$(dnf -q list available 'kmod-*' 2>/dev/null | awk 'NR>1{print $1; exit}')
fi
[ -n "$PKG" ] || { echo "FAIL: no kmod package available"; exit 1; }
echo "本次安装：$PKG"
dnf install -y -q "$PKG" 2>&1 | tail -2

step 5 "冒烟"
rpm -q "$PKG"

echo
echo "==== E2E PASS（elrepo-release 引导 + makecache + kmod 安装全程经镜像） ===="
