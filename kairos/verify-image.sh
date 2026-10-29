#!/usr/bin/env bash
set -euo pipefail

# No defaults on purpose: the versions to verify must be stated explicitly
# (build.py passes them from nodes.yaml).
image_ref="${1:?usage: verify-image.sh <image-ref> <expected-k3s-version>}"
expected_k3s_version="${2:?expected k3s version is required}"

docker run --rm --entrypoint /bin/bash \
  --env EXPECTED_K3S_VERSION="${expected_k3s_version}" \
  "${image_ref}" -lc '
set -euo pipefail

source /etc/kairos-release
test "${KAIROS_FLAVOR}" = ubuntu
test "${KAIROS_FLAVOR_RELEASE}" = 26.04
test "${KAIROS_VARIANT}" = standard
test "${KAIROS_SOFTWARE_VERSION_PREFIX}" = k3s
test "${KAIROS_SOFTWARE_VERSION}" = "${EXPECTED_K3S_VERSION}"

command -v stunnel4 >/dev/null
command -v zfs >/dev/null
command -v zpool >/dev/null
command -v k3s >/dev/null
test -x /system/providers/agent-provider-kairos
test -f /etc/systemd/system/k3s.service
test -f /etc/systemd/system/k3s-agent.service
k3s_version="$(k3s --version | awk "NR == 1 { print \$3 }")"
test "${k3s_version}" = "${EXPECTED_K3S_VERSION}"

kernel_count="$(find /usr/lib/modules -mindepth 1 -maxdepth 1 -type d | wc -l)"
test "${kernel_count}" -eq 1
kernel_dir="$(find /usr/lib/modules -mindepth 1 -maxdepth 1 -type d)"

for module in bonding zfs ixgbe igb bnxt_en smartpqi hpsa; do
  if ! find "${kernel_dir}" -type f -name "${module}.ko*" -print -quit | grep -q .; then
    echo "missing kernel module: ${module}" >&2
    exit 1
  fi
done

# The RAID, NIC, and bond drivers must be available before the immutable
# rootfs is mounted or early network configuration is evaluated. ZFS is
# intentionally loaded later from the rootfs.
initrd_listing="$(mktemp)"
trap "rm -f \"${initrd_listing}\"" EXIT
lsinitrd /boot/initrd > "${initrd_listing}"
for module in smartpqi hpsa ixgbe igb bnxt_en bonding; do
  if ! grep -q "/${module}\.ko" "${initrd_listing}"; then
    echo "kernel module is absent from initramfs: ${module}" >&2
    exit 1
  fi
done

# Per-node release ISOs provide their own MAC-matched network configuration.
# The broad default DHCP rules would race it and must not be in the image.
test ! -e /system/oem/05_network.yaml
test ! -e /system/oem/90_node.yaml

printf "Kairos: %s %s (%s)\n" \
  "${KAIROS_FLAVOR}" "${KAIROS_FLAVOR_RELEASE}" "${KAIROS_VERSION}"
printf "Variant: %s\n" "${KAIROS_VARIANT}"
printf "Provider: %s %s\n" \
  "${KAIROS_SOFTWARE_VERSION_PREFIX}" "${KAIROS_SOFTWARE_VERSION}"
printf "Kernel modules: %s\n" "${kernel_dir##*/}"
/system/providers/agent-provider-kairos version
k3s --version
stunnel4 -version
zfs_version="$(dpkg-query -W -f="\${Version}" zfsutils-linux)"
stunnel_version="$(dpkg-query -W -f="\${Version}" stunnel4)"
printf "zfsutils-linux: %s\n" "${zfs_version}"
printf "stunnel4: %s\n" "${stunnel_version}"
'

docker image inspect "${image_ref}" --format 'OCI image ID: {{.Id}}'
