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

# 参考 Homebrew 的打包方式，直接安装上游最新正式版。
# 本地重新构建时使用 --no-cache，避免复用旧的工具安装层。
# https://formulae.brew.sh/cask/codex
# https://formulae.brew.sh/cask/claude-code
# https://formulae.brew.sh/formula/uv
RUN <<'EOF'
set -eux

case "$(dpkg --print-architecture)" in
    amd64)
        rust_arch=x86_64
        claude_arch=x64
        ;;
    arm64)
        rust_arch=aarch64
        claude_arch=arm64
        ;;
    *)
        echo "不支持的架构：$(dpkg --print-architecture)" >&2
        exit 1
        ;;
esac

download_dir="$(mktemp -d)"
cd "$download_dir"

# 先解析 latest 到具体 tag，再从同一版本下载包；不调用 GitHub API。
codex_release="$(curl -fsSL --retry 3 -o /dev/null -w '%{url_effective}' \
    https://github.com/openai/codex/releases/latest)"
codex_base_url="https://github.com/openai/codex/releases/download/${codex_release##*/}"
codex_archive="codex-package-${rust_arch}-unknown-linux-musl.tar.gz"
curl -fL --retry 3 -o "$codex_archive" "${codex_base_url}/${codex_archive}"
# 保留 Codex 的包布局，供主程序定位沙箱等辅助程序与资源。
install -d -m 0755 /usr/local/bin /usr/local/lib/codex
tar -xzf "$codex_archive" -C /usr/local/lib/codex --no-same-owner
ln -s /usr/local/lib/codex/bin/codex /usr/local/bin/codex

claude_base_url=https://downloads.claude.ai/claude-code-releases
claude_version="$(curl -fsSL --retry 3 "${claude_base_url}/latest")"
curl -fL --retry 3 -o claude \
    "${claude_base_url}/${claude_version}/linux-${claude_arch}/claude"
install -m 0755 claude /usr/local/bin/claude

uv_release="$(curl -fsSL --retry 3 -o /dev/null -w '%{url_effective}' \
    https://github.com/astral-sh/uv/releases/latest)"
uv_base_url="https://github.com/astral-sh/uv/releases/download/${uv_release##*/}"
uv_archive="uv-${rust_arch}-unknown-linux-gnu.tar.gz"
curl -fL --retry 3 -o "$uv_archive" "${uv_base_url}/${uv_archive}"
mkdir uv
tar -xzf "$uv_archive" -C uv --strip-components=1 --no-same-owner
install -m 0755 uv/uv uv/uvx /usr/local/bin/

cd /
rm -rf "$download_dir"

codex --version
claude --version
uv --version
uvx --version
EOF

COPY tmux.conf /etc/tmux.conf
COPY --chmod=755 setup-mirror.sh /opt/setup-mirror.sh
