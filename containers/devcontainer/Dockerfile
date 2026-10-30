# https://mirrors.zju.edu.cn/container-images.md
ARG REGISTRY_MIRROR=""
# https://mcr.microsoft.com/en-us/artifact/mar/devcontainers/base/about
FROM ${REGISTRY_MIRROR}mcr.microsoft.com/devcontainers/base:debian

ARG DEBIAN_MIRROR=""

ENV DEBIAN_FRONTEND=noninteractive

RUN <<EOF
set -eux

if [ -n "${DEBIAN_MIRROR}" ]; then
    sed -i "s#http://deb.debian.org/debian#${DEBIAN_MIRROR}#g" \
        /etc/apt/sources.list.d/debian.sources
fi

apt-get update
apt-get install -y --no-install-recommends \
    bash \
    sudo \
    ca-certificates \
    gnupg \
    curl \
    jq \
    git \
    fish \
    python3 \
    build-essential \
    pkgconf \
    patch \
    make \
    file \
    less \
    rsync \
    openssh-client \
    bind9-dnsutils \
    openssl \
    tmux \
    shellcheck \
    shfmt \
    ripgrep \
    nodejs

apt-get distclean -y
EOF

COPY tmux.conf /etc/tmux.conf
COPY --chmod=755 setup-mirror.sh /opt/setup-mirror.sh
