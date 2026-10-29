FROM quay.io/kairos/kairos-init:v4.3.0 AS kairos-init

FROM ubuntu:26.04

# No defaults on purpose: build.py always passes both values from
# nodes.yaml, and a missing ARG must fail the build instead of silently
# producing an image with a stale version.
ARG KAIROS_VERSION
ARG K3S_VERSION

LABEL org.opencontainers.image.title="ZJU Mirror Kairos K3s image" \
      org.opencontainers.image.description="Ubuntu 26.04 Kairos image with the K3s provider" \
      org.opencontainers.image.source="https://github.com/ZJUSCT/mirrors.zju.edu.cn"

# stunnel wraps SSH in TLS so it passes the datacenter's SSH protocol DPI:
# sshd listens on loopback only and stunnel terminates TLS on the node's
# dual-stack address. The Ubuntu kernel already contains everything else the
# nodes need; Kairos itself installs zfsutils-linux and the matching Ubuntu
# ZFS module.
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      stunnel4 && \
    rm -rf /var/lib/apt/lists/*

# The K3s release is pinned rather than resolved from a moving release channel
# during the build. Cluster and node configuration remain separate from this
# provider image.
RUN --mount=type=bind,from=kairos-init,src=/kairos-init,dst=/kairos-init \
    /kairos-init -s install --provider k3s \
      --provider-k3s-version "${K3S_VERSION}" --version "${KAIROS_VERSION}"

# Every mirror node supplies a MAC-matched static bond configuration in its
# installer cloud-config.  Leaving Kairos' broad en*/eth* DHCP rules here would
# race that configuration during early boot and could put an address on a bond
# member, so the per-node configuration is mandatory for release ISOs.
RUN rm -f /system/oem/05_network.yaml

RUN --mount=type=bind,from=kairos-init,src=/kairos-init,dst=/kairos-init \
    /kairos-init -s init --provider k3s \
      --provider-k3s-version "${K3S_VERSION}" --version "${KAIROS_VERSION}"

# ZJU Mirror: replace the kairos-init GrubCfg template with a variant that
# anchors GRUB file/partition lookups to the already-resolved $root instead
# of device-wide "search" scans (see grub.cfg header), and ship an OEM stage
# that propagates it to COS_STATE after upgrades, which do not rewrite the
# installed GRUB config on their own.
COPY grub.cfg /etc/cos/grub.cfg
COPY grub-boot-speedup.yaml /system/oem/20_grub-boot-speedup.yaml
