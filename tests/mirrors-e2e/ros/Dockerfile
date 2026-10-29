# ROS 1 (Noetic) 镜像端到端测试：官方 ubuntu:20.04 容器（focal，ROS1
# Noetic 的目标平台，已 EOL）。基础源改指官方 old-releases.ubuntu.com
# （focal 已从 archive.ubuntu.com 下线）；ros.key 从 ROS 官方引导；ROS 1
# apt 源指向镜像，签名校验与下载全程走镜像。
FROM ubuntu:20.04
RUN apt-get update && apt-get install -y --no-install-recommends curl gnupg ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --chmod=755 e2e.sh /e2e.sh
ENTRYPOINT ["/e2e.sh"]
