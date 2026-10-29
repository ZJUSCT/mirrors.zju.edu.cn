#!/bin/sh
# Deepin CD 镜像端到端测试：结构验证（ISO 数 GB，不做全量下载，见 Dockerfile）。
# 校验链：目录列表取最新版本目录 -> amd64/ 下取 SHA256SUMS 与 ISO 条目 ->
# SHA256SUMS 覆盖该 ISO -> ISO 的 HEAD Content-Length 与列表 size 对账。
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
BASE="http://$MIRROR_HOST/deepin-cd"
step() { echo; echo "==== [${1}] ${2} ===="; }
get() { curl -s --noproxy '*' --max-time 30 "$@"; }

step 1 "解析最新版本目录"
# 目录列表为 JSON：{ "name":"25.2.0", ... }
VER=$(get "$BASE/" | grep -oE '"name":"[0-9]+\.[0-9.]+"' | sed 's/"name":"//;s/"//' | sort -V | tail -1)
[ -n "$VER" ] || { echo "FAIL: no version dir found"; exit 1; }
echo "最新版本：$VER"

step 2 "amd64/ 清单与校验文件"
LISTING=$(get "$BASE/$VER/amd64/")
echo "$LISTING" | grep -q "SHA256SUMS" || { echo "FAIL: SHA256SUMS missing"; exit 1; }
ISO=$(echo "$LISTING" | grep '"type":"file"' | grep '\.iso"' | grep -oE '"name":"[^"]+"' | sed 's/"name":"//;s/"//' | head -1)
[ -n "$ISO" ] || { echo "FAIL: no ISO in listing"; exit 1; }
SIZE=$(echo "$LISTING" | grep "\"name\":\"$ISO\"" | grep -oE '"size":[0-9]+' | sed 's/"size"://')
[ -n "$SIZE" ] || { echo "FAIL: no size for $ISO"; exit 1; }
echo "ISO：$ISO (列表 size $SIZE)"

step 3 "SHA256SUMS 覆盖该 ISO"
get "$BASE/$VER/amd64/SHA256SUMS" -o SHA256SUMS
grep -q "$ISO" SHA256SUMS || { echo "FAIL: $ISO not covered by SHA256SUMS"; exit 1; }
echo "OK: $(wc -l < SHA256SUMS) 条清单，含 $ISO"

step 4 "ISO HEAD Content-Length 对账"
CODE=$(get -o /dev/null -I -w "%{http_code}" "$BASE/$VER/amd64/$ISO")
[ "$CODE" = "200" ] || { echo "FAIL: HEAD ISO -> $CODE"; exit 1; }
LEN=$(get -I "$BASE/$VER/amd64/$ISO" | tr -d '\r' | awk 'tolower($1)=="content-length:"{print $2}')
[ "$LEN" = "$SIZE" ] || { echo "FAIL: size mismatch ($LEN != $SIZE)"; exit 1; }
echo "OK: Content-Length $LEN 与列表一致"

echo
echo "==== E2E PASS（版本目录/SHA256SUMS/ISO 尺寸 全部对账） ===="
