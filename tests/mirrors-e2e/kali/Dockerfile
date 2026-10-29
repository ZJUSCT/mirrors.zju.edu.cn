# Kali 镜像端到端测试：官方 kali-rolling 容器（自带 kali 密钥环）+
# sources.list 改指镜像站 -> apt update（Release/InRelease 签名校验）->
# 随机装一个小包并冒烟。
FROM kalilinux/kali-rolling
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates apt-transport-https \
    && rm -rf /var/lib/apt/lists/*
COPY --chmod=755 e2e.sh /e2e.sh
ENTRYPOINT ["/e2e.sh"]
