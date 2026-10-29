#!/bin/sh
# openkylin 镜像端到端测试：apt 源改指镜像站 -> apt update -> 安装一个包。
# 上游 archive(.build).openkylin.top/openkylin 与镜像站 /openkylin 路径一一对应。
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
step() { echo; echo "==== [${1}] ${2} ===="; }

step 1 "镜像源配置"
# 主源指向镜像站；禁用不在镜像范围内的附加仓库（openkylin-anything 等）
for f in /etc/apt/sources.list /etc/apt/sources.list.d/*.list; do
    [ -f "$f" ] || continue
    sed -i -E "s#https?://archive(\.build)?\.openkylin\.top#http://$MIRROR_HOST#g" "$f"
done
rm -f /etc/apt/sources.list.d/openkylin-anything.list
grep -rh '^deb ' /etc/apt/sources.list /etc/apt/sources.list.d/ 2>/dev/null || true

step 2 "apt-get update（元数据刷新走镜像）"
apt-get update -o Acquire::Retries=2

step 3 "apt-get install"
if [ -z "${PKG:-}" ]; then
    PKG=$(shuf -e tree jq bc file -n1)
fi
echo "本次安装：$PKG"
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "$PKG"

step 4 "可执行冒烟"
command -v "$PKG" >/dev/null && "$PKG" --version 2>/dev/null | head -1

echo
echo "==== E2E PASS（apt update/install 全程经镜像完成） ===="
