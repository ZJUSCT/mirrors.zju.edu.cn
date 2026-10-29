FROM alpine

RUN apk add --no-cache zsh rsync coreutils gawk findutils diffutils grep

ADD https://forge.fedoraproject.org/infra/quick-fedora-mirror.git /usr/local/src/qfm
COPY linkstat-rsync3.patch /tmp/linkstat-rsync3.patch
RUN <<'EOF'
set -xe
apk add --no-cache patch
patch --batch -p1 -d /usr/local/src/qfm < /tmp/linkstat-rsync3.patch
install -m 0755 /usr/local/src/qfm/quick-fedora-mirror /usr/local/bin/quick-fedora-mirror
rm -rf /usr/local/src/qfm /tmp/linkstat-rsync3.patch
EOF

WORKDIR /tmp
