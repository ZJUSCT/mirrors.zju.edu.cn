FROM debian:stable-slim AS source

RUN <<'EOF'
set -xe
apt-get update
apt-get install -y --no-install-recommends ca-certificates git
rm -rf /var/lib/apt/lists/*
EOF

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

FROM debian:stable-slim

RUN <<'EOF'
set -xe
apt-get update
apt-get install -y --no-install-recommends bash rsync gawk hostname
rm -rf /var/lib/apt/lists/*
EOF

COPY --from=source /ftpsync /ftpsync

ENV PATH=/ftpsync/bin:${PATH}
