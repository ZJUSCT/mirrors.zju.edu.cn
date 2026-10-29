#!/bin/sh
# ROS 2 镜像端到端测试：GPG key 从 ROS 官方引导（rosdistro ros.key，备用
# packages.ros.org/ros2.key）-> apt 源指向镜像（ros2/ubuntu，noble）->
# apt update（Release/InRelease 签名校验走镜像）-> 安装 ros-noble-ros-workspace
# （ROS 2 生态的基础包，依赖极轻）并冒烟。
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
step() { echo; echo "==== [${1}] ${2} ===="; }

step 1 "GPG key 引导（ROS 官方）"
install -d -m 0755 /usr/share/keyrings
if ! curl -fsSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
        -o /usr/share/keyrings/ros-archive-keyring.gpg; then
    echo "（rosdistro raw 不可达，改用 packages.ros.org/ros2.key）"
    curl -fsSL https://packages.ros.org/ros2.key -o /usr/share/keyrings/ros-archive-keyring.gpg
fi
gpg --show-keys /usr/share/keyrings/ros-archive-keyring.gpg | head -3

step 2 "apt 源指向镜像站"
. /etc/os-release
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://$MIRROR_HOST/ros2/ubuntu $VERSION_CODENAME main" \
    > /etc/apt/sources.list.d/ros2.list
cat /etc/apt/sources.list.d/ros2.list

step 3 "apt-get update（签名校验走镜像）"
apt-get update -o Acquire::Retries=2 2>&1 | tail -3

step 4 "安装 ros-jazzy-ros-workspace"
# noble 上的 ROS 2 发行版代号为 Jazzy，包前缀 ros-jazzy-*
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends ros-jazzy-ros-workspace

step 5 "冒烟"
dpkg -s ros-jazzy-ros-workspace | head -2
dpkg -L ros-jazzy-ros-workspace | head -3

echo
echo "==== E2E PASS（ROS 2 apt 仓库索引与包下载全程经镜像完成） ===="
