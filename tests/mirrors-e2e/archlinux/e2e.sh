#!/bin/sh
# Arch Linux 镜像端到端测试：pacman mirrorlist 改指镜像站 -> pacman -Sy
# （元数据刷新，包与仓库签名经 archlinux-keyring 校验）-> 安装一个包并
# 验证可执行。base 镜像预装了 file/diffutils 等基础工具，随机池避开它们。
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
step() { echo; echo "==== [${1}] ${2} ===="; }

step 1 "镜像源配置"
cat > /etc/pacman.d/mirrorlist <<EOF
Server = http://$MIRROR_HOST/archlinux/\$repo/os/\$arch
EOF
echo "mirror=$MIRROR_HOST"
grep Server /etc/pacman.d/mirrorlist

step 2 "pacman -Sy（元数据刷新，db 签名校验走镜像）"
pacman -Sy --noconfirm

step 3 "pacman -S 安装"
if [ -z "${PKG:-}" ]; then
    PKG=$(shuf -e tree jq bc cowsay -n1)
fi
echo "本次安装：$PKG"
pacman -S --noconfirm --needed "$PKG"

step 4 "可执行冒烟"
case "$PKG" in
    tree)    tree --version 2>&1 | head -1 ;;
    jq)      jq --version ;;
    bc)      echo '2^10' | bc ;;
    cowsay)  cowsay -t "e2e" | head -2 ;;
esac

echo
echo "==== E2E PASS（pacman -Sy/-S 全程经镜像完成） ===="
