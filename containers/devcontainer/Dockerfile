# https://mirrors.zju.edu.cn/container-images.md
ARG REGISTRY_MIRROR=""
# https://mcr.microsoft.com/en-us/artifact/mar/devcontainers/base/about
FROM ${REGISTRY_MIRROR}mcr.microsoft.com/devcontainers/base:alpine

# https://mirrors.zju.edu.cn/docs/alpine.md
ARG ALPINE_MIRROR=""

RUN <<EOF
set -xe

# 基础镜像已安装这些工具，仅从 apk add 清单省略不会移除它们。
remove_packages=""
for package in procps procps-ng psmisc lsof strace socat vim wget zip unzip xz; do
    if apk --no-network info --installed "$package" >/dev/null 2>&1; then
        remove_packages="$remove_packages $package"
    fi
done
if [ -n "$remove_packages" ]; then
    apk del --no-network $remove_packages
fi

# 注意：Alpine 默认的 BusyBox sed 不支持 GNU 扩展 \?，需分别匹配 http 与 https
if [ -n "${ALPINE_MIRROR}" ]; then
    sed -i \
        -e "s#http://dl-cdn.alpinelinux.org/alpine#${ALPINE_MIRROR}#g" \
        -e "s#https://dl-cdn.alpinelinux.org/alpine#${ALPINE_MIRROR}#g" \
        /etc/apk/repositories
fi

apk add --no-cache \
    bash \
    sudo \
    ca-certificates \
    gnupg \
    curl \
    jq \
    yq-go \
    yq-go-fish-completion \
    git \
    fish \
    python3 \
    build-base \
    pkgconf \
    patch \
    make \
    file \
    less \
    rsync \
    openssh-client-default \
    bind-tools \
    openssl \
    tmux \
    uv \
    uv-fish-completion \
    shellcheck \
    shfmt \
    ripgrep \
    nodejs \
    npm \
    docker-cli \
    docker-cli-buildx \
    docker-cli-compose \
    kubectl \
    helm

EOF

COPY tmux.conf /etc/tmux.conf

COPY --chmod=755 setup-mirror.sh /opt/setup-mirror.sh
