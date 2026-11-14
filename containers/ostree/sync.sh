#!/bin/sh
# OSTree 远程仓库镜像：首次运行时将 /data 初始化为 archive 仓库，随后执行
# pull --mirror 拉取 refs 与当前提交所需对象，成功后清理不可达对象，
# 不复制 static deltas。用法:
#   REMOTE_NAME=<name> sync-ostree <upstream-url>
# 可选 CONTENT_URL 指定独立的内容地址，支持 mirrorlist=<url>。
# GPG 校验由最终客户端负责，本层不验签。
set -eu

REMOTE_NAME="${REMOTE_NAME:?REMOTE_NAME must be set}"
REPO="${OSTREE_REPO:-/data}"
UPSTREAM="${1:?usage: sync-ostree <upstream-url>}"
CONTENT_URL="${CONTENT_URL:-}"

if [ ! -f "$REPO/config" ]; then
    ostree init --repo="$REPO" --mode=archive
fi

# remote 配置位于 repo config。每轮与 UPSTREAM 比对：不一致或
# 缺失时先删后建，一致时不改动。
CURRENT_URL="$(ostree --repo="$REPO" remote show-url "$REMOTE_NAME" 2>/dev/null || true)"
if [ "$CURRENT_URL" != "$UPSTREAM" ]; then
    [ -z "$CURRENT_URL" ] || ostree --repo="$REPO" remote delete "$REMOTE_NAME"
    ostree --repo="$REPO" remote add --no-gpg-verify "$REMOTE_NAME" "$UPSTREAM"
fi

# 将 CONTENT_URL 写入仓库的 contenturl 配置；为空时删除该配置项。
CONTENT_KEY="remote \"$REMOTE_NAME\".contenturl"
if [ -n "$CONTENT_URL" ]; then
    ostree --repo="$REPO" config set "$CONTENT_KEY" "$CONTENT_URL"
else
    ostree --repo="$REPO" config unset "$CONTENT_KEY"
fi

ostree --repo="$REPO" pull --mirror --network-retries=5 "$REMOTE_NAME"

# 仅在完整同步成功后清理，避免删除失败同步中可供下轮复用的对象。
# 与 pull 默认的 depth=0 保持一致，不保留仅由历史提交引用的对象。
exec ostree --repo="$REPO" prune --refs-only --depth=0
