# 静态投递（mirror-delivery）

服务 `https://mirrors.zju.edu.cn/delivery/` 路径，托管不构成镜像的临时静态内容
（活动页面等）。内容全部来自本目录下的 ConfigMap，不构建容器镜像。

## 结构与更新方式

- 每个「投递」是一个子目录（如 `math-pi-day-2026/`），由一个同名 ConfigMap
  挂载到 `/usr/share/nginx/html/delivery/<投递名>/`。
- 修改 HTML 或 `nginx.conf` 后直接提交：ConfigMap 名称固定（无哈希后缀），
  Reloader 会自动滚动更新 Pod，ArgoCD 正常同步即可，无需其他操作。
- 后端按主仓库 README 的 Small 档配置（2 worker，10m/32Mi 请求，
  4 CPU/256Mi 上限），调度倾向 `zjusct.io/pool=frontend`。
- HTTPRoute 挂在 `envoy-gateway-production`，PathPrefix `/delivery`；
  Gateway API 按最长前缀优先，因此不影响 mirror-front 的 `/` 兜底路由，
  也不与 Falcon 管理的镜像路径冲突。

## 容量与演进

- kube-apiserver 对单个 ConfigMap 的 data 总量限制为 1 MiB
  （所有 key 求和，etcd 中亦不压缩）。`math-pi-day-2026` 约 91 KiB。
- 某次投递超限时：优先按活动拆分为多个 ConfigMap（各挂载到各自子目录）；
  若投递成为常态且包含图片等大资源，应演进为独立仓库 + 容器镜像部署，
  路由与本目录的 Deployment/Service 结构可直接复用。

## 已知注意事项

- 页面引用 Google Fonts（`fonts.googleapis.com` / `fonts.gstatic.com`），
  `game1.html` 会向活动方的排行榜 API（页面内的 `LEADERBOARD_API`，
  `https://2026-pi-day.math.haoxx.me`）提交成绩；`nginx.conf` 的 CSP 已放行
  相应来源。
- 排行榜服务的 CORS 允许来源需要包含 `https://mirrors.zju.edu.cn`，否则
  成绩提交会静默失败（页面代码吞掉了错误，仅不再显示排名）。上线前应与
  活动方确认。
- 目录请求（如 `/delivery/math-pi-day-2026/`）按镜像发布源的目录契约返回
  autoindex JSON，本服务不提供前端浏览壳页面。
