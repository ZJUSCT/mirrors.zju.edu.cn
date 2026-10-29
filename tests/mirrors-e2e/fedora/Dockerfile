FROM fedora:latest
RUN dnf -y install dnf-plugins-core && dnf clean all
COPY e2e.sh /e2e.sh
ENTRYPOINT ["/bin/sh", "/e2e.sh"]
