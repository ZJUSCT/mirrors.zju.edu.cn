#!/bin/sh
# Deepin 镜像端到端测试：结构验证（无官方客户端容器，见 Dockerfile 说明）。
# 校验链：dists/apricot/Release 内的 SHA256 -> 下载 Packages.gz 对账 ->
# 从索引取一个包的 Filename/Size -> HEAD 包本体对账 Content-Length。
# 即 APT 客户端消费的元数据链在镜像上是自洽的；GPG 签名校验缺锚点未覆盖。
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
BASE="http://$MIRROR_HOST/deepin"
step() { echo; echo "==== [${1}] ${2} ===="; }
get() { curl -s --noproxy '*' --max-time 30 "$@"; }
WORK=$(mktemp -d)
cd "$WORK"

step 1 "Release 文件与 Packages 索引哈希"
get "$BASE/dists/apricot/Release" -o Release
grep -q "^SHA256:" Release || { echo "FAIL: no SHA256 section in Release"; exit 1; }
LINE=$(awk '/^SHA256:/{f=1; next} /^[A-Za-z]+:$/{f=0} f && / main\/binary-amd64\/Packages\.gz$/' Release)
[ -n "$LINE" ] || { echo "FAIL: Packages.gz not in Release SHA256 section"; exit 1; }
EXPECT=$(echo "$LINE" | awk '{print $1}' | tail -1)
echo "Release 记录的 Packages.gz sha256: $EXPECT"

step 2 "下载 Packages.gz 并校验 SHA256"
get "$BASE/dists/apricot/main/binary-amd64/Packages.gz" -o Packages.gz
ACTUAL=$(sha256sum Packages.gz | awk '{print $1}')
[ "$ACTUAL" = "$EXPECT" ] || { echo "FAIL: sha256 mismatch ($ACTUAL != $EXPECT)"; exit 1; }
echo "OK: Packages.gz sha256 一致"

step 3 "从索引取包并对账包本体大小"
# 取索引中最后一个 stanza 的 Filename/Size（避开被裁剪的前部字段）
PAIR=$(zcat Packages.gz | awk -F': ' '$1=="Filename"{f=$2} $1=="Size"{s=$2} END{print f, s}')
FN=$(echo "$PAIR" | awk '{print $1}')
SZ=$(echo "$PAIR" | awk '{print $2}')
[ -n "$FN" ] && [ -n "$SZ" ] || { echo "FAIL: cannot parse Packages index"; exit 1; }
echo "包：$FN (Size $SZ)"
CODE=$(get -o /dev/null -I -w "%{http_code}" "$BASE/$FN")
[ "$CODE" = "200" ] || { echo "FAIL: HEAD $FN -> $CODE"; exit 1; }
LEN=$(get -I "$BASE/$FN" | tr -d '\r' | awk 'tolower($1)=="content-length:"{print $2}')
[ "$LEN" = "$SZ" ] || { echo "FAIL: size mismatch ($LEN != $SZ)"; exit 1; }
echo "OK: 包本体 Content-Length 与索引一致"

rm -rf "$WORK"
echo
echo "==== E2E PASS（Release->Packages->包本体 元数据链自洽） ===="
