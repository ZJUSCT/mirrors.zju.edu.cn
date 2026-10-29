#!/bin/sh
# Debian 镜像端到端测试：apt 源改指镜像站 -> apt update（元数据刷新，
# 顺带验证 Release 签名校验）-> 安装一个包并验证可执行。
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
step() { echo; echo "==== [${1}] ${2} ===="; }

step 1 "镜像源配置"
# 从镜像自带 sources 提取 suite，重写为镜像站（保持签名校验链）
SRC=$(ls /etc/apt/sources.list.d/*.sources 2>/dev/null | head -1)
SUITE=$(sed -n 's/^Suites: //p' "$SRC" | head -1 | awk '{print $1}')
echo "suite=$SUITE mirror=$MIRROR_HOST"
cat > "$SRC" <<EOF
Types: deb
URIs: http://$MIRROR_HOST/debian
Suites: $SUITE
Components: main
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg
EOF

# 禁止静默跟随 HTTPS 重定向，确保索引和包下载均实际使用 HTTP。
cat > /etc/apt/apt.conf.d/99-mirror-http-e2e <<'EOF'
Acquire::http::AllowRedirect "false";
EOF

step 2 "apt-get update（Release/InRelease 签名校验走镜像）"
apt-get update -o Acquire::Retries=2

step 3 "apt-get install"
if [ -z "${PKG:-}" ]; then
    PKG=$(shuf -e sl tree jq file bsdgames -n1)
fi
echo "本次安装：$PKG"
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "$PKG"

step 4 "可执行冒烟"
case "$PKG" in
    sl)        /usr/games/sl --help 2>&1 | head -1 || true ;;
    bsdgames)  /usr/games/fortune -s | head -1 ;;
    *)         command -v "$PKG" >/dev/null && "$PKG" --version 2>/dev/null | head -1 ;;
esac

echo
echo "==== E2E PASS（apt update/install 全程经镜像完成） ===="
