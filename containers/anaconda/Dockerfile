FROM debian:testing-slim

RUN <<'EOF'
set -xe
apt-get update
apt-get install -y --no-install-recommends python3 python3-pyquery python3-requests curl gzip patch
rm -rf /var/lib/apt/lists/*
EOF

ADD https://github.com/tuna/tunasync-scripts/raw/master/anaconda.py /usr/local/src/anaconda.py
COPY nvidia-cloud-repo.patch /tmp/nvidia-cloud-repo.patch
COPY parallel-memory.patch /tmp/parallel-memory.patch

RUN <<'EOF'
set -xe
patch --batch -p1 -d /usr/local/src < /tmp/nvidia-cloud-repo.patch
patch --batch -p1 -d /usr/local/src < /tmp/parallel-memory.patch
install -m 0755 /usr/local/src/anaconda.py /usr/local/bin/anaconda
rm -rf /usr/local/src /tmp/nvidia-cloud-repo.patch /tmp/parallel-memory.patch
EOF

USER 65532:65532

WORKDIR /tmp
