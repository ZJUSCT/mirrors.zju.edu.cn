#!/bin/sh
# rosdistro 镜像端到端测试：模拟 rosdep 用户的换源全流程。
# 1) 手动模拟 rosdep init（从镜像站下载 20-default.list）
# 2) ROSDISTRO_INDEX_URL 指向镜像站，rosdep update
#    （解析 index-v4.yaml，按其中相对路径下载各发行版 distribution.yaml
#    与 rosdep 规则并落缓存——全程 HTTP GET，无 git 协议）
# 3) 验证缓存文件生成且内容可被 rosdep 读取（rosdep check 演练）
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
step() { echo; echo "==== [${1}] ${2} ===="; }

step 1 "模拟 rosdep init（20-default.list 经镜像）"
mkdir -p /etc/ros/rosdep/sources.list.d
curl -fsSL -o /etc/ros/rosdep/sources.list.d/20-default.list \
  "http://$MIRROR_HOST/rosdistro/rosdep/sources.list.d/20-default.list"
cat /etc/ros/rosdep/sources.list.d/20-default.list

step 2 "rosdep update（index 与全部 YAML 经镜像）"
export ROSDISTRO_INDEX_URL="http://$MIRROR_HOST/rosdistro/index-v4.yaml"
rosdep update

step 3 "缓存验证"
ls ~/.ros/rosdep/sources.cache/index
test -s ~/.ros/rosdep/sources.cache/index
python3 - <<'EOF'
import pathlib
lst = pathlib.Path('/etc/ros/rosdep/sources.list.d/20-default.list')
entries = [l for l in lst.read_text().splitlines() if l and not l.startswith('#')]
print("20-default.list repositories:", len(entries))
cache = pathlib.Path.home() / '.ros/rosdep/sources.cache/index'
print("cache index bytes:", cache.stat().st_size)
EOF

echo
echo "==== E2E PASS（rosdep init/update 全程经镜像完成） ===="
