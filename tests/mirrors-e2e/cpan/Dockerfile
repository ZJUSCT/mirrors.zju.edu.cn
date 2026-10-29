# CPAN 镜像端到端测试：官方 perl 容器 + CPAN 客户端经镜像安装模块。
# 设 o conf urllist 指向镜像后，cpan 客户端拉索引（authors/01mailrc、
# modules/02packages）并下载、构建、安装一个真实发行版。
# 注意：CPAN 首次运行有交互式配置，用 -T（trust）+ 环境变量全跳过。
FROM perl:5.41
COPY --chmod=755 e2e.sh /e2e.sh
ENTRYPOINT ["/e2e.sh"]
