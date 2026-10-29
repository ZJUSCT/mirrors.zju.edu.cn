#!/bin/sh
# ImmortalWrt 镜像端到端测试：结构验证 + 小镜像全量 sha256 校验。
# 解析最新 release -> 遍历 targets/<t>/<s>/ 找带 sha256sums 且含 ≤10MB
# img.gz 的子目录 -> 全量下载镜像 -> 与官方 sha256sums 对账。
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
BASE="http://$MIRROR_HOST/immortalwrt/releases"
step() { echo; echo "==== [${1}] ${2} ===="; }
get() { curl -s --noproxy '*' --max-time 120 "$@"; }
WORK=$(mktemp -d)
cd "$WORK"

step 1 "解析最新 release"
VER=$(get "$BASE/" | grep -oE '"name":"2[0-9]\.[0-9]+\.[0-9]+"' | sed 's/"name":"//;s/"//' | sort -V | tail -1)
[ -n "$VER" ] || { echo "FAIL: no release version found"; exit 1; }
echo "最新版本：$VER"

step 2 "定位带小镜像的 targets 子目录"
FOUND=""
for T in $(get "$BASE/$VER/targets/" | grep -oE '"name":"[^"]+"' | sed 's/"name":"//;s/"//' | head -4); do
    for S in $(get "$BASE/$VER/targets/$T/" | grep -oE '"name":"[^"]+"' | sed 's/"name":"//;s/"//' | head -3); do
        D="$VER/targets/$T/$S"
        L=$(get "$BASE/$D/")
        echo "$L" | grep -q "sha256sums" || continue
        IMG=$(echo "$L" | grep '"type":"file"' | grep '\.img\.gz"' | \
            awk -v s='"size":' '{ if (match($0, s"[0-9]+")) { sz=substr($0, RSTART+length(s), RLENGTH-length(s)); if (sz+0 > 0 && sz+0 <= 10485760) { match($0, /"name":"[^"]+"/); print substr($0, RSTART+8, RLENGTH-9), sz; exit } } }')
        if [ -n "$IMG" ]; then
            FOUND="$D"; IMGFILE=$(echo "$IMG" | awk '{print $1}'); IMGSZ=$(echo "$IMG" | awk '{print $2}')
            break 2
        fi
    done
done
[ -n "$FOUND" ] || { echo "FAIL: no target dir with small image found"; exit 1; }
echo "目录：$FOUND；镜像：$IMGFILE (size $IMGSZ)"

step 3 "下载 sha256sums 与镜像（全量）"
get "$BASE/$FOUND/sha256sums" -o sha256sums

get "$BASE/$FOUND/$IMGFILE" -o "$IMGFILE"
ls -l "$IMGFILE"

step 4 "sha256 对账"
# 上游 sha256sums 为 `hash *filename` 二进制模式格式（星号分隔）
EXPECT=$(grep -F "*$IMGFILE" sha256sums | awk '{print $1}' | head -1)
[ -n "$EXPECT" ] || EXPECT=$(grep " $IMGFILE\$" sha256sums | awk '{print $1}' | head -1)
[ -n "$EXPECT" ] || { echo "FAIL: $IMGFILE not in sha256sums"; exit 1; }
ACTUAL=$(sha256sum "$IMGFILE" | awk '{print $1}')
[ "$ACTUAL" = "$EXPECT" ] || { echo "FAIL: sha256 mismatch"; exit 1; }
echo "OK: sha256 一致（$ACTUAL）"

rm -rf "$WORK"
echo
echo "==== E2E PASS（ImmortalWrt 镜像全量下载且 sha256 校验通过） ===="
