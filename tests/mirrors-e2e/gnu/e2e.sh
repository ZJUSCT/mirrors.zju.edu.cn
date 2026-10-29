#!/bin/sh
# GNU 镜像端到端测试：官方 gnu-keyring.gpg 引导（ftp.gnu.org）-> 从镜像
# 下载 bash 源码包与其 .sig -> GPG 签名校验（GNU 密钥环）-> tar 结构冒烟。
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
BASE="http://$MIRROR_HOST/gnu"
step() { echo; echo "==== [${1}] ${2} ===="; }
WORK=$(mktemp -d)
cd "$WORK"

step 1 "GNU keyring 引导（官方 ftp.gnu.org）"
curl -fsSL --max-time 30 https://ftp.gnu.org/gnu/gnu-keyring.gpg -o keyring.gpg
gpg --no-default-keyring --keyring ./keyring.gpg --list-keys | grep -c pub | head -1

step 2 "从镜像下载 bash 源码包与签名"
# GNU 保留全部历史版本，固定版本稳定；bash-5.3 发布于 2025-12
PKG=bash-5.3.tar.gz
curl -fsSL --max-time 120 "$BASE/bash/$PKG" -o "$PKG"
curl -fsSL --max-time 30 "$BASE/bash/$PKG.sig" -o "$PKG.sig"
ls -l "$PKG"

step 3 "GPG 签名校验（GNU 密钥环，gpgv）"
# alpine 的 gpg 默认 keyboxd 会忽略自定义 keyring，用 gpgv 做纯校验
gpgv --keyring ./keyring.gpg "$PKG.sig" "$PKG"
echo "签名校验 OK"

step 4 "tar 结构冒烟"
tar -tzf "$PKG" | head -3

echo
echo "==== E2E PASS（GNU 源码包经镜像下载且 GPG 签名验证通过） ===="
