FROM alpine AS source

RUN apk add --no-cache git

ADD --keep-git-dir=true https://ftp-master.debian.org/git/archvsync.git /ftpsync

COPY archvsync-container-logging.patch archvsync-upstream-uip-recheck.patch /tmp/
RUN <<'EOF'
set -xe
revision="$(git -C /ftpsync rev-parse --short HEAD)"
sed -i "s/^VERSION=.*/VERSION=\"g${revision}\"/" /ftpsync/bin/include-git
git -C /ftpsync apply --check /tmp/archvsync-container-logging.patch
git -C /ftpsync apply /tmp/archvsync-container-logging.patch
git -C /ftpsync apply --check /tmp/archvsync-upstream-uip-recheck.patch
git -C /ftpsync apply /tmp/archvsync-upstream-uip-recheck.patch
rm -rf /ftpsync/.git /tmp/archvsync-container-logging.patch /tmp/archvsync-upstream-uip-recheck.patch
EOF

FROM alpine

RUN apk add --no-cache bash rsync

COPY --from=source /ftpsync /ftpsync

ENV PATH=/ftpsync/bin:${PATH}
