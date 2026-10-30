#!/usr/bin/env bash
# 容器启动后可按需执行 sudo /opt/setup-mirror.sh，配置包管理器镜像。

set -euo pipefail

MIRROR="${MIRROR:-mirrors.zju.edu.cn}"
DEBIAN_MIRROR="https://${MIRROR}/debian"
PYPI_MIRROR="https://${MIRROR}/pypi/web/simple"
NPM_REGISTRY="https://registry.npmmirror.com/"

sed -i "s#http://deb.debian.org/debian#${DEBIAN_MIRROR}#g" \
    /etc/apt/sources.list.d/debian.sources

cat >/etc/pip.conf <<EOF
[global]
index-url = ${PYPI_MIRROR}
EOF

install -d -m 0755 /etc/uv
cat >/etc/uv/uv.toml <<EOF
[[index]]
url = "${PYPI_MIRROR}/"
default = true
EOF

cat >/etc/npmrc <<EOF
registry=${NPM_REGISTRY}
EOF

# 环境变量型镜像注入到各 Shell 配置文件中
#
# install -d -m 0755 /etc/profile.d
# cat >/etc/profile.d/goproxy.sh <<EOF
# export GO111MODULE=on
# export GOPROXY=https://goproxy.cn
# EOF
#
# install -d -m 0755 /etc/fish/conf.d
# cat >/etc/fish/conf.d/goproxy.fish <<EOF
# set -gx GO111MODULE on
# set -gx GOPROXY https://goproxy.cn
# EOF
