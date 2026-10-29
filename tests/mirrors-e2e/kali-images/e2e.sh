#!/bin/sh
# Kali Images 镜像端到端测试：结构验证（ISO 数 GB，不做全量下载）。
# 校验链：kali-weekly/ 下取 SHA256SUMS 与 ISO 条目 -> SHA256SUMS 覆盖该
# ISO -> ISO 的 HEAD Content-Length 与目录列表 size 对账。
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
BASE="http://$MIRROR_HOST/kali-images"
step() { echo; echo "==== [${1}] ${2} ===="; }
get() { curl -s --noproxy '*' --max-time 30 "$@"; }

step 1 "取 kali-weekly 目录清单"
LISTING=$(get "$BASE/kali-weekly/")
echo "$LISTING" | grep -q "SHA256SUMS" || { echo "FAIL: SHA256SUMS missing"; exit 1; }
ISO=$(echo "$LISTING" | grep '"type":"file"' | grep '\.iso"' | grep -oE '"name":"[^"]+"' | sed 's/"name":"//;s/"//' | head -1)
[ -n "$ISO" ] || { echo "FAIL: no ISO in listing"; exit 1; }
SIZE=$(echo "$LISTING" | grep "\"name\":\"$ISO\"" | grep -oE '"size":[0-9]+' | sed 's/"size"://')
[ -n "$SIZE" ] || { echo "FAIL: no size for $ISO"; exit 1; }
echo "ISO：$ISO (列表 size $SIZE)"

step 2 "SHA256SUMS 覆盖该 ISO"
get "$BASE/kali-weekly/SHA256SUMS" -o SHA256SUMS
grep -q "$ISO" SHA256SUMS || { echo "FAIL: $ISO not covered by SHA256SUMS"; exit 1; }
echo "OK: $(wc -l < SHA256SUMS) 条清单，含 $ISO"

step 3 "ISO HEAD Content-Length 对账"
CODE=$(get -o /dev/null -I -w "%{http_code}" "$BASE/kali-weekly/$ISO")
[ "$CODE" = "200" ] || { echo "FAIL: HEAD ISO -> $CODE"; exit 1; }
LEN=$(get -I "$BASE/kali-weekly/$ISO" | tr -d '\r' | awk 'tolower($1)=="content-length:"{print $2}')
[ "$LEN" = "$SIZE" ] || { echo "FAIL: size mismatch ($LEN != $SIZE)"; exit 1; }
echo "OK: Content-Length $LEN 与列表一致"

echo
echo "==== E2E PASS（kali-weekly SHA256SUMS/ISO 尺寸对账完成） ===="
