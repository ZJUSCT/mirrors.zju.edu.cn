# rosdistro 镜像端到端测试：官方 rosdep 容器（含 rosdep/rospkg 工具链），
# 模拟用户侧完整流程：rosdep init（curl 20-default.list）→
# ROSDISTRO_INDEX_URL 指向镜像 → rosdep update（解析 index 并下载全部
# distribution/rosdep YAML）→ 验证缓存生成。
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* && pip install --no-cache-dir rosdep rospkg catkin_pkg
COPY --chmod=755 e2e.sh /e2e.sh
ENTRYPOINT ["/e2e.sh"]
