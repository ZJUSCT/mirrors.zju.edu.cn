#!/bin/sh
# CentOS Stream 端到端测试：dnf 源改指镜像站 9-stream（BaseOS/AppStream
# repodata 签名校验）-> dnf makecache -> 安装一个包并验证可执行。
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
STREAM=9-stream
step() { echo; echo "==== [${1}] ${2} ===="; }

step 1 "镜像源配置"
mkdir -p /etc/yum.repos.d.bak && mv /etc/yum.repos.d/* /etc/yum.repos.d.bak/ 2>/dev/null || true
cat > /etc/yum.repos.d/mirror.repo <<EOF
[baseos]
name=CentOS Stream $STREAM - BaseOS
baseurl=http://$MIRROR_HOST/centos-stream/$STREAM/BaseOS/\$basearch/os/
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-centosofficial

[appstream]
name=CentOS Stream $STREAM - AppStream
baseurl=http://$MIRROR_HOST/centos-stream/$STREAM/AppStream/\$basearch/os/
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-centosofficial
EOF
cat /etc/yum.repos.d/mirror.repo

step 2 "dnf makecache（元数据刷新，repomd 签名校验走镜像）"
dnf makecache -q --setopt=install_weak_deps=False

step 3 "dnf install"
if [ -z "${PKG:-}" ]; then
    PKG=$(shuf -e tree jq bc -n1)
fi
echo "本次安装：$PKG"
dnf install -y -q --setopt=install_weak_deps=False "$PKG"

step 4 "可执行冒烟"
case "$PKG" in
    tree) tree --version 2>&1 | head -1 ;;
    jq)   jq --version ;;
    bc)   echo '2^10' | bc ;;
esac

echo
echo "==== E2E PASS（dnf makecache/install 全程经镜像完成） ===="
