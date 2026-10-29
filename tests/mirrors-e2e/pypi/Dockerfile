# PyPI 镜像端到端测试：官方 python 镜像 + pip 指向镜像站 simple 索引。
FROM python:3.12-slim
COPY --chmod=755 e2e.sh /e2e.sh
ENTRYPOINT ["/e2e.sh"]
