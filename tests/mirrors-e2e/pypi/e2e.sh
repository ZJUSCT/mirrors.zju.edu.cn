#!/bin/sh
# PyPI 镜像端到端测试：pip index-url 指向镜像站 simple 索引，
# 元数据（simple index）与包本体（packages/）均应走镜像。
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
INDEX="http://$MIRROR_HOST/pypi/web/simple"
step() { echo; echo "==== [${1}] ${2} ===="; }

step 1 "pip 与镜像源配置"
pip --version
echo "index-url: $INDEX"

step 2 "安装一个包（simple 索引 + wheel 均走镜像）"
if [ -z "${PKG:-}" ]; then
    PKG=$(shuf -e six toml idna certifi pyyaml -n1)
fi
echo "本次安装：$PKG"
# pip 默认拒绝 HTTP 索引；仅信任本次测试指定的镜像域名。
pip install --no-cache-dir --trusted-host "$MIRROR_HOST" --index-url "$INDEX" "$PKG"

step 3 "导入冒烟"
python - "$PKG" <<'EOF'
import importlib, sys
pkg = sys.argv[1].replace('-', '_')
m = importlib.import_module(pkg)
print(f"import {pkg}: OK (version={getattr(m, '__version__', 'n/a')})")
EOF

echo
echo "==== E2E PASS（pip 元数据与包下载全程经镜像完成） ===="
