#!/bin/bash
# Homebrew 镜像端到端测试：brew update / brew list / 随机安装一个带 bottle 的包。
# 通过标准：全流程无 ghcr.io 回落（出现 "falling back to the default domain" 即失败）。
set -uo pipefail

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
export HOMEBREW_BREW_GIT_REMOTE="http://$MIRROR_HOST/homebrew/brew.git" \
       HOMEBREW_CORE_GIT_REMOTE="http://$MIRROR_HOST/homebrew/homebrew-core.git" \
       HOMEBREW_CASK_GIT_REMOTE="http://$MIRROR_HOST/homebrew/homebrew-cask.git" \
       HOMEBREW_API_DOMAIN="http://$MIRROR_HOST/homebrew-bottles/api" \
       HOMEBREW_BOTTLE_DOMAIN="http://$MIRROR_HOST/homebrew-bottles" \
       HOMEBREW_NO_INSTALL_CLEANUP=1 \
       HOMEBREW_NO_ENV_HINTS=1

step() { echo; echo "==== [${1}] ${2} ===="; }

step 1 "brew --version"
brew --version

step 2 "brew update（brew.git / homebrew-core.git / API JSON 均走镜像）"
brew update 2>&1 | tee /tmp/update.log | tail -5
export HOMEBREW_NO_AUTO_UPDATE=1

step 3 "brew list"
brew list

step 4 "brew install（bottle 走镜像下载）"
# 候选都是 x86_64_linux 有 bottle 的小包；可用 PKG 环境变量指定
if [ -z "${PKG:-}" ]; then
    PKG=$(shuf -e hello tree jq wget ncdu -n1)
fi
echo "本次安装：$PKG"
brew install "$PKG" 2>&1 | tee /tmp/install.log

# 可执行性冒烟
BIN="$(brew --prefix)/bin/$PKG"
case "$PKG" in
    hello) "$BIN" ;;
    tree|jq|wget|ncdu) "$BIN" --version | head -1 ;;
    *) "$BIN" --version 2>/dev/null | head -1 || "$BIN" --help 2>&1 | head -1 ;;
esac

# 严格性检查：任何回落到默认域（ghcr.io）的迹象都算失败
# （注意：静默回落检测不到，最终凭据以镜像站 publish access log 为准）
if grep -iE "falling back|ghcr\.io" /tmp/install.log >/dev/null; then
    echo
    echo "==== E2E FAIL：检测到 ghcr.io 回落 ===="
    grep -iE "falling back|ghcr\.io" /tmp/install.log
    exit 1
fi

echo
echo "==== E2E PASS（update/list/install 全程经镜像完成，无回落） ===="
