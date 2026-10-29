# openEuler 镜像端到端测试：官方 24.03 LTS 容器 + dnf 源指向镜像站。
# 官方镜像自带 openeuler-gpg-keys（包签名校验链）与 ca-certificates。
FROM openeuler/openeuler:24.03-lts
RUN yum install -y ca-certificates && yum clean all
COPY --chmod=755 e2e.sh /e2e.sh
ENTRYPOINT ["/e2e.sh"]
