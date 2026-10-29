#!/bin/sh
set -eu

# 只修正 PVC 根目录的 owner；不递归，不修改 group/mode，保留 bitflip 权限。
# SYNC_UID 必须与实际同步容器的 runAsUser 一致。
case "${SYNC_UID:-}" in
    ''|*[!0-9]*) echo "SYNC_UID 必须是非零数字 UID" >&2; exit 1 ;;
esac
[ "$SYNC_UID" -gt 0 ] && [ "$SYNC_UID" -lt 4294967295 ]
[ -d /data ] && [ ! -L /data ]
if [ "$(stat -c '%u' /data)" != "$SYNC_UID" ]; then
    chown "$SYNC_UID" /data
fi
[ "$(stat -c '%u' /data)" = "$SYNC_UID" ]
stat -c 'sync volume root: uid=%u gid=%g mode=%a' /data
