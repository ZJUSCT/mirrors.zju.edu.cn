FROM rust:1-alpine AS builder

RUN apk add --no-cache build-base

RUN cargo install tsumugu --locked --root /out

FROM alpine

RUN apk add --no-cache ca-certificates

COPY --from=builder /out/bin/tsumugu /usr/local/bin/tsumugu

WORKDIR /tmp
