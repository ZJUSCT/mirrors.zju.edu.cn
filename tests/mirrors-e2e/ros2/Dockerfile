# ROS 2 镜像端到端测试：官方 ubuntu:24.04 容器 + ROS 2 apt 源指向镜像。
# GPG key 引导自 ROS 官方（rosdistro 的 ros.key / packages.ros.org，与官方
# 安装文档一致，避免从镜像自身取 key 的循环信任）；此后 Release/包签名
# 校验与下载全程走镜像。
FROM ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends curl gnupg ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --chmod=755 e2e.sh /e2e.sh
ENTRYPOINT ["/e2e.sh"]
