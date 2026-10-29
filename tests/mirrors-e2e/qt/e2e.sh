#!/bin/sh
# Qt 镜像端到端测试：从镜像下载官方在线安装器 -> 尺寸对账 -> 文件类型
# 冒烟（run 文件为 shell/ELF 混合格式）。
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
step() { echo; echo "==== [${1}] ${2} ===="; }
BASE="http://$MIRROR_HOST/qt/official_releases/online_installers"
WORK=$(mktemp -d)
cd "$WORK"

step 1 "镜像源配置"
echo "mirror=$BASE"

step 2 "获取目录列表并解析安装器尺寸（经镜像）"
LIST=$(wget -qO- "$BASE/")
F="qt-online-installer-linux-x64-online.run"
EXPECT=$(echo "$LIST" | grep -oE "\"name\":\"$F\",[^}]*\"size\":[0-9]+" | grep -oE "[0-9]+$" | head -1)
[ -n "$EXPECT" ] || { echo "cannot resolve installer size"; exit 1; }
echo "installer: $F ($EXPECT bytes)"

step 3 "下载安装器（经镜像）"
wget -q "$BASE/$F"
ACTUAL=$(stat -c %s "$F")
echo "downloaded: $ACTUAL bytes"
[ "$ACTUAL" = "$EXPECT" ]

step 4 "文件类型冒烟"
file "$F" | grep -qiE "script|executable|elf" || { file "$F"; exit 1; }
head -c 64 "$F" | grep -qa "#!/bin/sh" && echo "Qt online installer (shell stub) OK"

echo
echo "==== E2E PASS（Qt 在线安装器下载全程经镜像完成） ===="
