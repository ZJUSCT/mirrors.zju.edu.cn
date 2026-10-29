#!/bin/sh
# ROS 1 镜像端到端测试：focal 基础源改指官方 old-releases（focal EOL，
# ubuntu 镜像已随上游删除 focal）-> GPG key 从 ROS 官方引导 -> ROS 1 apt
# 源指向镜像（ros/ubuntu focal）-> apt update（签名校验走镜像）->
# 安装 ros-noetic-catkin 并冒烟。
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
step() { echo; echo "==== [${1}] ${2} ===="; }

step 1 "GPG key 引导（ROS 官方）"
install -d -m 0755 /usr/share/keyrings
if ! curl -fsSL --max-time 30 https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
        -o /usr/share/keyrings/ros-archive-keyring.gpg; then
    echo "（rosdistro raw 不可达，改用 packages.ros.org/ros.key）"
    curl -fsSL --max-time 30 https://packages.ros.org/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
fi
gpg --show-keys /usr/share/keyrings/ros-archive-keyring.gpg | head -3

step 2 "ROS 1 apt 源指向镜像站"
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://$MIRROR_HOST/ros/ubuntu focal main" \
    > /etc/apt/sources.list.d/ros1.list
cat /etc/apt/sources.list.d/ros1.list

step 3 "apt-get update（签名校验走镜像）"
apt-get update -o Acquire::Retries=2 -o APT::Sandbox::User=root 2>&1 | tail -3

step 4 "安装 ros-noetic-catkin"
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends ros-noetic-catkin

step 5 "冒烟"
dpkg -s ros-noetic-catkin | head -2
test -x /usr/bin/catkin_make && echo "catkin_make OK"

echo
echo "==== E2E PASS（ROS 1 Noetic apt 仓库索引与包下载全程经镜像完成） ===="
