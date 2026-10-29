# openkylin 镜像端到端测试：官方容器 + apt 通过 HTTP 访问镜像站。
# 不额外注入 CA 证书，覆盖精简容器的纯 HTTP 使用场景。
FROM openkylin/openkylin:3.0
COPY --chmod=755 e2e.sh /e2e.sh
ENTRYPOINT ["/e2e.sh"]
