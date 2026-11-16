#!/bin/sh
# 为官方 mirror.sh 提供 TLS 传输和本站 rsync 参数。
set -eu

export RSYNC_CONNECT_PROG='openssl s_client -quiet -verify_return_error -verify_hostname repos.fyralabs.com -servername repos.fyralabs.com -connect repos.fyralabs.com:874'

exec rsync -H --no-o --no-g --safe-links \
    --stats --itemize-changes \
    --partial-dir=.rsync-partial --filter='P .rsync-partial/' \
    --exclude='.~tmp~/' --delete-excluded \
    --filter="merge ${TERRA_FILTER_FILE:?TERRA_FILTER_FILE must be set}" \
    --timeout=120 --contimeout=120 "$@"
