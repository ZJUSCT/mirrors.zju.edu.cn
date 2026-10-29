#!/bin/sh
# Rustup 镜像端到端测试：rustup-init 从官方 static.rust-lang.org 引导并做
# sha256 校验 -> RUSTUP_DIST_SERVER/RUSTUP_UPDATE_ROOT 指向镜像 -> 安装
# stable 最小工具链（rustc/cargo/标准库全部经镜像下载）-> 编译运行冒烟。
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
step() { echo; echo "==== [${1}] ${2} ===="; }

step 1 "rustup-init 引导（官方 static.rust-lang.org，TLS 信任锚）"
curl -fsSL https://static.rust-lang.org/rustup/dist/x86_64-unknown-linux-gnu/rustup-init -o /tmp/rustup-init
chmod +x /tmp/rustup-init
# 镜像完整性交叉核验：镜像的 rustup-init 与官方逐字节一致
curl -fsSL "http://$MIRROR_HOST/rustup/rustup/dist/x86_64-unknown-linux-gnu/rustup-init" -o /tmp/rustup-init.mirror
cmp /tmp/rustup-init /tmp/rustup-init.mirror && echo "镜像与官方 rustup-init 逐字节一致"
rm -f /tmp/rustup-init.mirror

step 2 "安装 stable 最小工具链（组件全部经镜像下载）"
export RUSTUP_DIST_SERVER="http://$MIRROR_HOST/rustup"
export RUSTUP_UPDATE_ROOT="http://$MIRROR_HOST/rustup/rustup"
/tmp/rustup-init -y --profile minimal --default-toolchain stable --no-modify-path 2>&1 | tail -3

step 3 "版本冒烟"
"$HOME/.cargo/bin/rustc" --version
"$HOME/.cargo/bin/cargo" --version

step 4 "编译运行冒烟（证明工具链组件完整可用）"
WORK=$(mktemp -d)
cd "$WORK"
export PATH="$HOME/.cargo/bin:$PATH"
cargo new hello --bin -q
cd hello
cargo run -q > /tmp/cargo-run.out 2>&1
grep -q "Hello, world!" /tmp/cargo-run.out || { cat /tmp/cargo-run.out; echo "FAIL: 编译运行冒烟未输出预期结果"; exit 1; }
echo "cargo run OK"

rm -rf "$WORK"
echo
echo "==== E2E PASS（rustup 工具链下载全程经镜像完成，可编译运行） ===="
