#!/bin/sh
# CentOS（老布局）端到端测试：结构验证。镜像内容形态仿 TUNA——中空骨架
# （TIME 心跳文件、timestamp.txt、全版本目录、HEADER.html），真实包内容
# 由 centos-vault 镜像承接（该镜像有独立的 yum e2e）。通过标准：全部
# 标志性工件 HTTP 200 且内容非空。
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
BASE="http://$MIRROR_HOST/centos"
step() { echo; echo "==== [${1}] ${2} ===="; }

check() {
    code=$(curl -s --noproxy '*' -o /tmp/body -w "%{http_code}" --max-time 15 "$1")
    size=$(wc -c < /tmp/body)
    [ "$code" = "200" ] || { echo "FAIL: $1 -> $code"; exit 1; }
    [ "$size" -gt 0 ] || { echo "FAIL: $1 -> empty body"; exit 1; }
    echo "OK: $1 ($size bytes)"
}

step 1 "同步心跳工件"
check "$BASE/TIME"
check "$BASE/timestamp.txt"

step 2 "版本目录与骨架"
check "$BASE/7.9.2009/"
check "$BASE/8-stream/"
check "$BASE/HEADER.html"

step 3 "目录列表协商"
curl -s --noproxy '*' --max-time 15 "$BASE/7.9.2009/" -H "Accept: application/json" | grep -q '"name"' \
    || { echo "FAIL: JSON listing missing"; exit 1; }
echo "OK: JSON listing served"

echo
echo "==== E2E PASS（骨架工件全部可达） ===="
