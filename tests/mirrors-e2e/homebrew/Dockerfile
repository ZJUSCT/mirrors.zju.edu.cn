# Homebrew 镜像端到端测试：官方 brew 镜像 + 镜像站环境变量。
# MIRROR_HOST 作为运行时环境变量注入（compose environment），无需重新构建。
FROM ghcr.io/homebrew/brew:latest
COPY --chmod=755 e2e.sh /e2e.sh
ENTRYPOINT ["/bin/bash", "/e2e.sh"]
