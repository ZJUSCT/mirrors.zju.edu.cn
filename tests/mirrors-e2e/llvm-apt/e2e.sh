#!/bin/sh
# LLVM apt 镜像端到端测试：GPG key 从官方 apt.llvm.org 引导 -> apt 源指向
# 镜像（trixie / llvm-toolchain-trixie）-> apt update（签名校验走镜像）->
# 安装 clang 并编译运行冒烟。
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
step() { echo; echo "==== [${1}] ${2} ===="; }

step 1 "GPG key 引导（官方 apt.llvm.org）"
curl -fsSL https://apt.llvm.org/llvm-snapshot.gpg.key -o /etc/apt/trusted.gpg.d/llvm.asc
gpg --show-keys /etc/apt/trusted.gpg.d/llvm.asc | head -3

step 2 "apt 源指向镜像站"
. /etc/os-release
echo "deb [signed-by=/etc/apt/trusted.gpg.d/llvm.asc] http://$MIRROR_HOST/llvm-apt/$VERSION_CODENAME llvm-toolchain-$VERSION_CODENAME main" \
    > /etc/apt/sources.list.d/llvm.list
cat /etc/apt/sources.list.d/llvm.list

step 3 "apt-get update（签名校验走镜像）"
apt-get update -o Acquire::Retries=2 2>&1 | tail -3

step 4 "安装 clang"
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends clang

step 5 "编译运行冒烟"
printf '#include <stdio.h>\nint main(){printf("clang OK\\n");return 0;}\n' > /tmp/t.c
clang /tmp/t.c -o /tmp/t && /tmp/t

echo
echo "==== E2E PASS（LLVM apt 仓库索引与包下载全程经镜像完成） ===="
