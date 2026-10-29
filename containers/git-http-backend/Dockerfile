FROM nginxinc/nginx-unprivileged:mainline-alpine-otel
USER root
RUN apk add --no-cache fcgiwrap spawn-fcgi git git-daemon && test -x /usr/libexec/git-core/git-http-backend
USER 101
