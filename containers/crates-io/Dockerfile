FROM ustcmirror/crates-io:latest

# Patch based on ustclug/ustcmirror-images commit 41488ca8a63b2c95596137a41d2b3c547bfacf59.
COPY crates-io-sha256.patch /tmp/crates-io-sha256.patch
RUN <<'EOF'
set -xe
cd /
git apply --check -p2 /tmp/crates-io-sha256.patch
git apply -p2 /tmp/crates-io-sha256.patch
rm /tmp/crates-io-sha256.patch
EOF
