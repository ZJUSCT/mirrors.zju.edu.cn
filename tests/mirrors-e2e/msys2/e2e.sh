#!/bin/sh
# MSYS2 镜像端到端测试：pacman（archlinux base 容器，与 msys2 仓库格式同源）
# 以 msys2 仓库配置指向镜像站 -> pacman -Sy 元数据刷新（db 经镜像下载）->
# 从 db 随机选包 -> 包体下载 -> SHA256 与 db 记录对账 -> zstd/tar 结构冒烟。
# msys2 包为 Windows PE，无法在 Linux 安装执行，安装语义以校验和解包替代；
# db/包体签名属 msys2 密钥环（Linux 容器内不可用），完整性由 SHA256 对账保证。
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
step() { echo; echo "==== [${1}] ${2} ===="; }
BASE="http://$MIRROR_HOST/msys2"
WORK=$(mktemp -d)
cd "$WORK"

step 1 "pacman.conf 指向镜像站"
# SigLevel=Never：签名校验需 msys2 密钥环，改为依赖第 5 步的 SHA256 对账
cat > pacman.conf <<EOF
[options]
HoldPkg = pacman glibc
Architecture = x86_64
SigLevel = Never
LocalFileSigLevel = Never

[ucrt64]
Server = $BASE/mingw/ucrt64/

[msys]
Server = $BASE/msys/x86_64/
EOF
grep Server pacman.conf

step 2 "pacman -Sy（仓库 db 经镜像下载）"
pacman --config pacman.conf -Sy
ls -l /var/lib/pacman/sync/*.db

step 3 "从 db 随机选包（>200MB 的巨型包不入池）"
: > pairs.txt
for repo in ucrt64 msys; do
    mkdir -p "db-$repo" && tar -xf "/var/lib/pacman/sync/$repo.db" -C "db-$repo"
    for d in "db-$repo"/*/; do
        [ -f "$d/desc" ] || continue
        f=$(awk '/^%FILENAME%$/{getline; print; exit}' "$d/desc")
        s=$(awk '/^%SHA256SUM%$/{getline; print; exit}' "$d/desc")
        z=$(awk '/^%SIZE%$/{getline; print; exit}' "$d/desc")
        [ -n "$f" ] && [ -n "$s" ] && [ "${z:-0}" -lt 200000000 ] || continue
        echo "$repo $f $s" >> pairs.txt
    done
done
N=$(wc -l < pairs.txt)
[ "$N" -gt 0 ] || { echo "db 解析失败，无可用包"; exit 1; }
if [ -n "${PKG:-}" ]; then
    LINE=$(grep "^ucrt64 $PKG" pairs.txt | head -1 || grep -m1 "$PKG" pairs.txt)
    [ -n "$LINE" ] || { echo "未找到指定包 $PKG"; exit 1; }
else
    LINE=$(sed -n "$(shuf -i 1-"$N" -n1)p" pairs.txt)
fi
REPO=$(echo "$LINE" | awk '{print $1}')
FNAME=$(echo "$LINE" | awk '{print $2}')
SHA=$(echo "$LINE" | awk '{print $3}')
echo "选中：$REPO/$FNAME（共 $N 个候选）"

step 4 "包体下载（经镜像）"
curl -fsSLO "$BASE/mingw/ucrt64/$FNAME" || curl -fsSLO "$BASE/msys/x86_64/$FNAME"
ls -l "$FNAME"

step 5 "SHA256 对账（与 db 记录比对）"
echo "$SHA  $FNAME" | sha256sum -c -

step 6 "zstd/tar 结构冒烟"
zstd -t "$FNAME"
tar --zstd -tf "$FNAME" | head -3

echo
echo "==== E2E PASS（pacman db 刷新与随机包下载校验全程经镜像完成） ===="
