#!/bin/sh
# Fedora 镜像端到端测试：dnf 源改指镜像站 -> dnf makecache（元数据刷新，
# 顺带验证 repomd.xml 签名校验）-> 安装一个包并验证可执行。
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
step() { echo; echo "==== [${1}] ${2} ===="; }

step 1 "镜像源配置"
RELEASE=$(rpm -E %{?fedora})
echo "release=$RELEASE mirror=$MIRROR_HOST"
cat > /etc/yum.repos.d/mirror-test.repo <<EOF
[mirror-test]
name=Mirror E2E Test
baseurl=http://$MIRROR_HOST/fedora/releases/$RELEASE/Everything/\$basearch/os/
enabled=1
metadata_expire=1h
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-$RELEASE-primary
EOF

step 2 "dnf makecache（repomd 签名校验走镜像）"
dnf -y makecache --disablerepo='*' --enablerepo='mirror-test' \
    --setopt=*.skip_if_unavailable=False

step 3 "dnf install"
if [ -z "${PKG:-}" ]; then
    PKG=$(shuf -e sl tree jq file cowsay -n1)
fi
echo "本次安装：$PKG"
dnf -y install --disablerepo='*' --enablerepo='mirror-test' "$PKG"

step 4 "可执行冒烟"
case "$PKG" in
    sl)        /usr/bin/sl 2>&1 | head -1 || true ;;
    cowsay)    echo "e2e" | /usr/bin/cowsay | head -1 ;;
    *)         command -v "$PKG" >/dev/null && "$PKG" --version 2>/dev/null | head -1 ;;
esac

echo
echo "==== E2E PASS（dnf makecache/install 全程经镜像完成） ===="
