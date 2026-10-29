#!/bin/sh
# CentOS Vault 端到端测试：yum 源改指镜像站 vault 树（7.9.2009 = CentOS 7
# 最终版，os/updates/extras 三仓库 repodata 齐全）-> yum makecache（元数据
# 刷新）-> 安装一个包并验证可执行。随机池避开基础镜像预装工具。
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
RELEASE=7.9.2009
step() { echo; echo "==== [${1}] ${2} ===="; }

step 1 "镜像源配置"
mkdir -p /etc/yum.repos.d.bak && mv /etc/yum.repos.d/* /etc/yum.repos.d.bak/ 2>/dev/null || true
cat > /etc/yum.repos.d/mirror.repo <<EOF
[base]
name=CentOS-$RELEASE - Base
baseurl=http://$MIRROR_HOST/centos-vault/$RELEASE/os/\$basearch/
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-CentOS-7

[updates]
name=CentOS-$RELEASE - Updates
baseurl=http://$MIRROR_HOST/centos-vault/$RELEASE/updates/\$basearch/
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-CentOS-7

[extras]
name=CentOS-$RELEASE - Extras
baseurl=http://$MIRROR_HOST/centos-vault/$RELEASE/extras/\$basearch/
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-CentOS-7
EOF
cat /etc/yum.repos.d/mirror.repo

step 2 "yum makecache（元数据刷新，repomd 签名校验走镜像）"
yum makecache fast -q

step 3 "yum install"
if [ -z "${PKG:-}" ]; then
    PKG=$(shuf -e tree bc time -n1)
fi
echo "本次安装：$PKG"
yum install -y -q "$PKG"

step 4 "可执行冒烟"
case "$PKG" in
    tree) tree --version 2>&1 | head -1 ;;
    bc)   echo '2^10' | bc ;;
    time) command -v time ;;
esac

echo
echo "==== E2E PASS（yum makecache/install 全程经镜像完成） ===="
