# CentOS（老布局）端到端测试：结构验证。TUNA 布局下 centos 模块本身是
# 中空骨架（版本目录存在但包内容在 centos-vault，见 CR 头部调查），无法
# 做包管理器级测试；本测试验证骨架的标志性工件完整可达（TIME/timestamp/
# 版本目录列表/HEADER），以及目录列表协商正常。
FROM alpine:3.20
RUN apk add --no-cache curl
COPY --chmod=755 e2e.sh /e2e.sh
ENTRYPOINT ["/e2e.sh"]
