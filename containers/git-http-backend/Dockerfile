FROM nginxinc/nginx-unprivileged:mainline-otel
USER root
RUN <<'EOF'
set -xe
apt-get update
apt-get install -y --no-install-recommends ca-certificates fcgiwrap spawn-fcgi git
rm -rf /var/lib/apt/lists/*

test -x /usr/sbin/fcgiwrap
test -x /usr/lib/git-core/git-http-backend
EOF
USER 101
