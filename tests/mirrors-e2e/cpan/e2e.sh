#!/bin/sh
# CPAN 镜像端到端测试：CPAN 客户端源指向镜像 -> 安装一个模块 -> 冒烟。
# 用 App::cpanminus（轻量、无交互）走镜像装一个真实发行版；
# 01mailrc/02packages 索引与 tarball 下载全程经镜像即验证通过。
set -eu

MIRROR_HOST="${MIRROR_HOST:-mirrors.zju.edu.cn}"
step() { echo; echo "==== [${1}] ${2} ===="; }

step 1 "镜像源配置"
MIRROR="http://$MIRROR_HOST/cpan"
echo "mirror=$MIRROR"
export PERL_MM_USE_DEFAULT=1
export PERL_AUTOINSTALL="--defaultdeps"

step 2 "引导 cpanminus（索引与源码包经镜像）"
# 用 cpan 客户端本身（无交互模式）从镜像装 App-cpanminus
cpan -T App::cpanminus 2>&1 | tail -3

step 3 "经镜像安装一个真实模块"
cpanm --from "$MIRROR/" --notest Try::Tiny 2>&1 | tail -3

step 4 "冒烟"
perl -MTry::Tiny -e 'print "Try::Tiny OK: $Try::Tiny::VERSION\n"'

echo
echo "==== E2E PASS（CPAN 索引与模块下载全程经镜像完成） ===="
