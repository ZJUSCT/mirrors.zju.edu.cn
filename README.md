<h1 align="center">
  <img src="mirror.svg" alt="Falcon" width="48">
  mirrors.zju.edu.cn<br>
</h1>

本仓库存放了第三代 [浙江大学镜像站（ZJU Mirror）](https://mirrors.zju.edu.cn/) 的开源 GitOps 配置。

本仓库 Issue 接收关于 ZJU Mirror 的：

- Mirror Requests / 镜像请求
- Bug Report / 故障报告
- Others / 其他事项

如果你希望为 ZJU Mirror 作出**贡献**：

- 请确保你已经完整阅读本文，了解镜像站的工作原理。
- 本仓库对 AI 贡献的态度是「Responsible Use Of Generative AI」，可参考：

    - [General resolution: LLM usage in Debian: Results](https://lists.debian.org/debian-devel-announce/2026/08/msg00005.html)
    - [AI 工具使用注意事项 - Linux 201](https://201.ustclug.org/spec/writing/#ai-tools)

- Commit 需要签名。
- 通过 Review 和 PR 合入。

## 为什么开源本仓库？

- 长久以来，各高校镜像站通过开源与技术分享交流经验，在互相借鉴与讨论中共同提升。例如：

    - [tuna/tunasync](https://github.com/tuna/tunasync)：TUNA 的镜像同步管理器被众多镜像站采用；
    - [sjtug/mirror-clone](https://github.com/sjtug/mirror-clone)：SJTUG 探索了基于对象存储提供镜像服务；
    - [镜像站 ZFS 实践 - LUG @ USTC](https://lug.ustc.edu.cn/planet/2024/12/ustc-mirrors-zfs-rebuild/)：USTCLUG 的 ZFS 实践经验帮助 ZJU Mirror 和更多镜像站优化存储配置。

    不同的镜像站根据自身硬件条件、技术偏好和历史沿革，做出了多样化的架构选择。据笔者所知，ZJU Mirror 是目前 CERNET 内为数不多的基于 Kubernetes 构建并公开实践经验的镜像站。我们希望将配置开源出来，为镜像站社区的技术方案补充一种可能性和参考样例。

- 镜像站作为开源生态的基础设施，将脱敏后的运行配置开源在社区中有充分的先例。许多成熟的开源项目与基础设施均采取了这一做法，例如：

    - [jenkins.debian.net](https://salsa.debian.org/qa/jenkins.debian.net)
    - [archlinux/infrastructure](https://gitlab.archlinux.org/archlinux/infrastructure)
    - [kde/sysadmin](https://invent.kde.org/sysadmin)
    - [开源镜像站 - LUG @ USTC](https://docs.ustclug.org/services/mirrors/)
    - [金枪鱼之夜：2023 年秋季学期迎新会 & TUNA 镜像站服务架构演进 | 清华大学 TUNA 协会](https://tuna.moe/event/2023/welcome-and-mirrors-infra/)
    - [Home · sjtug/mirror-docker-unified Wiki](https://github.com/sjtug/mirror-docker-unified/wiki)

- 通用的开源收益：

    - 为有类似架构需求或对云原生部署感兴趣的团队提供可直接参考的样例；
    - 借由社区的审查与建议，帮助我们发现潜在配置缺陷，持续优化自身的运行策略。

## License

本项目的原创文档、Kubernetes 资源配置文件及脚本采用 [Apache License 2.0](LICENSE) 许可发布。

本仓库中部分包含上游默认配置的文件（例如 `apps/*/values` 目录下拷贝自原 Chart 并修改的 `values.yaml` 文件）：

- 属于对应上游 Helm Chart / 开源项目的衍生作品。
- 其版权归属于原作者/上游社区。
- 这些文件的使用与分发严格遵循其上游项目各自对应的开源许可证。

---

下文是笔者认为镜像站贡献者应当掌握的知识。下文不会介绍 K8s 相关内容，因为网络上已有丰富的学习资料。

## 目录

- [ZJU Mirror 的软硬件架构](#zju-mirror-的软硬件架构)
- [ArgoCD 与 GitOps](#argocd-与-gitops)
- [镜像站的工作原理](#镜像站的工作原理)
- [如何维护本仓库的镜像](#如何维护本仓库的镜像)

## ZJU Mirror 的软硬件架构

### 硬件

浙江大学镜像站所有的硬件资源都是由 [浙江大学信息技术中心](http://zuits.zju.edu.cn/) 赞助的，属于 [研在浙大·科研软件平台](https://soft.zju.edu.cn/) 的一个子项目。

2025 年 4 月，我们从信息技术中心收到了第三代镜像站的硬件设施，物理位置位于浙江大学紫金港校区和同苑 5 幢化四 221 G6 机柜。新一代镜像站由 3 台存储节点、2 台业务节点构成，通过万兆交换机（H3C S6520X-24ST-SI）互联，该交换机的连接情况如下：

- 上游交换机：10G SFP+，镜像站集群到校网的总带宽受限于此
- 两台业务节点：2 x 10G SFP+ 链路聚合（LACP）
- 三台存储节点：4 x 10G SFP+ 链路聚合（LACP）

官方资料：

- 存储服务器：[H3C X10536 G3](https://www.h3c.com/cn/Service/Document_Software/Document_Center/Storage/Catalog/Massive_Scale_Out/H3C_UniStor_X10000_G3/)
- 业务服务器：[H3C R4900 G3](https://www.h3c.com/cn/Service/Document_Software/Document_Center/Server/Catalog/Rack_server/H3C_UniServer_R4900_G3/)
- 网卡：[Support - 02-PCIe network adapter specifications- H3C](https://www.h3c.com/en/Support/Resource_Center/EN/Severs/Catalog/Optional_Parts/Network_Adapter/Technical_Documents/Product_Literature/Card_Datasheets/Network_Adapter_Datasheet/202206/1616867_294551_0.htm)：新华三网卡数据表。
- RAID 卡：[Support - 08-Configuring an H460, P460, P240 or P4408 storage controller- H3C](https://www.h3c.com/en/Support/Resource_Center/EN/Home/Severs/00-Public/Software_Configure/User_Manual/H3C_Servers_Storage_Controller_UG/202207/1655190_294551_0.htm)：RAID 卡配置手册。

存储服务器：

- CPU：2 x Intel Xeon Silver 4110
- 内存：8 x 32GB DDR4 2666MHz RDIMM

- 存储规格：每台配备 2 张 H3C P460 RAID 卡，具有 4GB 缓存和掉电保护。

    | 数量 | 容量 | 类型 | 具体型号 |
    | --- | --- | --- | --- |
    | 2 | 600G | 12 Gbps SAS HDD 系统盘 | SEAGATE ST600MM0009 |
    | 6 | 480GB | 12 Gbps SATA SSD 数据盘 | Micron 5200 MTFD |
    | 30 | 8TB | 12 Gbps SATA HDD 数据盘 | SEAGATE ST8000NM0055-1RM |

    系统盘已配置为 RAID1。

- 网络规格：每台配备 2 张双口 10G 以太网卡和 1 张双 1G 以太网卡。

    | 插槽 | 网卡型号 | 规格 | 控制器 |
    | --- | --- | --- | --- |
    | 板载 | NIC-GE-2P-360T-B2-1-X | 2 x 1GE RJ45 | Intel NHI350AM |
    | PCIe | CNA-10GE-2P-560F-B2-1 | 2 x 10GE SFP | Intel JL82599 |
    | FLOM | NIC-10GE-2P-560F-LOM | 2 x 10GE SFP | Intel JL82599 |

业务服务器：

- CPU：2 x Intel Xeon Gold 6130
- 内存：6 x 16GB DDR4 2666MHz RDIMM

- 存储规格：每台配备 1 张 H3C P460 RAID 卡，具有 4GB 缓存 和掉电保护。

    | 数量 | 容量 | 类型 | 具体型号 |
    | --- | --- | --- | --- |
    | 2 | 600G | 12 Gbps SAS HDD 系统盘 | SEAGATE ST600MM0009 |

    系统盘已配置为 RAID1。

- 网络规格：每台配备 1 张双口 10G 以太网卡。

    | 插槽 | 网卡型号 | 规格 | 控制器 |
    | --- | --- | --- | --- |
    | PCIe | NIC-BCM957302-F-B-10Gb-2P | 2 x 10GE SFP | Broadcom BCM57302 |

交换机：

| 参数 | 值 |
| --- | --- |
| 前面板业务端口描述 | 24 个 1/2.5/10GE SFP Plus 端口（2 个 Combo 1G/2.5G/5G/10G Base-T 自适应以太网端口） |
| 交换容量 | 2.56Tbps/25.6Tbps |
| 包转发率 | 360Mpps |
| 链路聚合 | 支持 10GE 端口聚合 |

#### 固件版本

2025 年 4 月刷入 H3C 提供的最新固件：

- UniStor X10536 G3
    - HDM: 1.11.35P06 HDM V100R001B02D035SP06
    - BIOS: 2.00.52 V100R001B02D052
- UniServer R4900 G3
    - HDM: 3.54
    - BIOS: 2.00.66

特别地，存储服务器使用的 Micro 5200 SSD 最初的固件是 `D1MU008`。该版本固件在通电小时数超过 65535 后会导致磁盘性能下降到不可接受的程度。经验证，升级到 `D1MU040` 版本固件可修复问题。此后，如果 SSD 更换该系列的备件，需要检查固件版本并升级。参考资料：

- [WARNING: MICRON 5200 fails after 65535 hours : r/DataHoarder](https://www.reddit.com/r/DataHoarder/comments/1sly734/warning_micron_5200_fails_after_65535_hours/)，目前使用的固件也是从这里的评论区下载的。
- [PowerEdge: Micron 5x00 Series solid state drive Performance Degradation after 65,535 POH | Dell Hong Kong](https://www.dell.com/support/kbdoc/en-hk/000464492/poweredge-micron-5xxx-series-solid-state-drive-performance-degradation-after-65-535-poh)

#### 定位损坏的磁盘

镜像站磁盘损坏应当联系信息中心进行更换，镜像站运维需要负责定位损坏的磁盘：

- 如果是直通盘，则使用 `hwinfo --disk` 可以看到 Model 和 Serial Number，据此去带外管理的 Storage 选项卡搜索即可。
- 如果是逻辑卷：
    - RAID 卡检测到坏盘后，会在带外管理中标记逻辑卷状态为 `Failed`，可直接定位。
    - RAID 卡尚未检测到磁盘损坏，而系统报错，则可以根据 SysFS 路径进行定位。以下面的路径为例：

        ```text
        // 内核日志，出现该日志的时候控制器已检测到磁盘损坏，会直接掉盘
        tag#741 received 'logical unit failure' from controller for scsi 14:1:0:9
        // hwinfo 信息
        SysFS BusID: 14:1:0:9
        SysFS Device Link: /devices/pci0000:3a/0000:3a:00.0/0000:3b:00.0/host14/target14:1:0/14:1:0:9
        ```

        将 BusID 的字段分为 0~3。

        | 字段 | 解释 |
        | --- | --- |
        | 0 | 控制器编号 |
        | 1 | 设备类型，逻辑卷为 `1`，直通盘为 `0` |
        | 2 | 直通盘序号 |
        | 3 | 逻辑卷序号 |

        比如上面的设备为逻辑卷 9，可以在带外管理中找到对应的逻辑卷。

### Kairos

[Kairos](https://github.com/kairos-io/kairos) 是一个专为 K8s 设计的不可变 Linux 发行版，它是镜像站所有节点上部署的 OS。

- 它的声明式配置使用 [yip](https://github.com/mudler/yip)，语法基于 [cloud-init](https://github.com/canonical/cloud-init) 但不完全相同，需要仔细核对。
- 系统仍基于 Ubuntu，包括 ZFS DKMS 等都来自上游。可以理解为 Kairos 只是帮助做好了不可变镜像打包、A/B recovery 机制、原子化升级等方便的包装。

选择 [K3s](https://github.com/k3s-io/k3s) 而不是标准 K8s 的原因：

- Kairos 原生支持 K3s
- K3s 核心组件简单，运维复杂度低
- K3s 内置一些方便的功能，例如内置 [Spegel Registry](https://github.com/spegel-org/spegel)、镜像 URL 重写等

修改现有节点的 Kairos 或 K3s 配置时，需要同时：

- 更新仓库中的模板或节点配置，保证以后生成的镜像包含变更。
- 更新受影响节点的 `/oem/90_custom.yaml`，保证变更在重启后仍然存在。`/oem` 很容易被遗漏，只修改 `/etc` 下当前生效的文件可能在重启后被覆盖。
- 如果变更需要立即生效，还要更新当前运行系统中的相应配置，并按服务要求重载或重启。

升级 Kairos：

- 将 OCI 镜像传输到节点上，用 kairos-agent 和 ocifile 方式升级。
- 升级只会刷写系统镜像，不会修改 `/oem` 下的声明式配置，如有变更记得手动更新。

### 网络

对公网**上行**带宽限速：v4/v6 各 100Mbps，其余没有限制。

CERNET 的 v6 资源比 v4 更加充裕，同步任务偏好使用 v6 进行。

#### STunnel 和 SSH 访问

镜像站所处的机房受到信息技术中心的加强防护，全端口做 SSH 阻断。因此，Kairos 做如下配置

- sshd 仅监听本地 22 端口
- stunnel 监听双栈 22222，仅转发到本地 22 端口

stunnel 自身仅负责 TLS 终结和到本地 22 的固定流量转发，几乎没有攻击面。攻击者就算终结了 TLS，仍要面对 SSH 公钥认证，可以认为该措施是相当安全的。

不过平常也很少需要使用 SSH 登录到宿主机。几乎所有运维任务都能够通过 K8s API 完成，包括部分宿主机的运维任务。

### K3s

- 启用双栈网络支持。但 Pod 网络的 IPv6 是 ULA，glibc 和 musl 都按 RFC 6724 Rule 2 判 ULA 源为 scope 不匹配，把 v4 地址排在前面。为了使用 v6 网络，rsync 等工具需要显式添加 `-6` 选项。
- 节点打 label 分为两组：
    - `zjusct.io/pool=frontend`：适合无状态，只需要 CPU 和内存的服务（例如 Gateway 和流量分析聚合等）
    - `zjusct.io/pool=storage`：适合需要持久化存储的服务

部分 Registry 无法直连，通过 [DaoCloud/public-image-mirror](https://github.com/DaoCloud/public-image-mirror) 等可信任的公共 Registry Mirror 拉取，这由 K3s 的 `registries.yaml` 重写处理，见 [kairos/cloud-config.yaml.j2](kairos/cloud-config.yaml.j2)。

- 能够直接访问的 Registry：

    ```text
    quay.io
    ghcr.io
    nvcr.io
    registry.gitlab.com
    public.ecr.aws
    mcr.microsoft.com
    docker.elastic.co
    lscr.io
    docker.osgeo.org
    ```

- 不能直接访问的 Registry：

    ```text
    docker.io
    registry-1.docker.io
    hub.docker.com
    registry.k8s.io # 它本身可访问，但 302 到 pkg.dev 属于 Google 无法访问
    *.gcr.io
    ```

### K8s 上的服务

#### 本地存储：[openebs/zfs-localpv](https://github.com/openebs/zfs-localpv)

zfs-localpv 用于管理存储节点上的 HDD，存储镜像内容。

每个存储节点上，按如下方式创建 zpool 和 dataset。选盘的时候注意按磁盘控制器做负载均衡，例如 HDD 每个 RAIDZ2 组中，有 4 个盘来自一个磁盘控制器，另外 6 个盘来自另一个磁盘控制器。

```sh
# pool: openebs-hdd
zpool create \
  -o ashift=12 \
  -o autotrim=off \
  -O mountpoint=none \
  -O compression=lz4 \
  -O atime=off \
  -O xattr=sa \
  -O acltype=posixacl \
  -O dedup=off \
  openebs-hdd \
  raidz2 /dev/disk/by-id/... # <共三组 RAIDZ2，每组 10 盘>
zfs create \
  -o canmount=off \
  -o mountpoint=none \
  -o recordsize=1M \
  -o compression=zstd-3 \
  -o atime=off \
  -o xattr=off \
  -o acltype=off \
  -o setuid=off \
  -o exec=off \
  -o devices=off \
  -o dedup=off \
  -o sync=standard \
  -o redundant_metadata=all \
  openebs-hdd/openebs
# 完成后检查
zpool status -P
zpool list
zfs get -r \
  mountpoint,canmount,recordsize,compression,dedup,atime,acltype,xattr,exec,setuid,devices,sync,redundant_metadata \
  openebs-hdd
```

为 K8s 应用提供的 StorageClass 见 `apps/openebs/resources/storageclasses.yaml`。

#### 分布式多类型存储：[rook](https://github.com/rook/rook)

Rook Ceph 用于管理存储节点上的 SSD，提供分布式高可用的块、文件系统和对象存储，适用于一般工作负载。

- `ceph-block`：适合 RWO
- `ceph-filesystem`：适合 RWX
- `ceph-bucket`：对象存储

2026-09-21 调优后 Benchmark 结果：

- RADOS Bench：
    - replicated write：971 MiB/s
    - 稳态读：1.23–1.36 GiB/s 
- kernel RBD（QD 16）：
    - 4 KiB random-read IOPS：15.2k
    - 4 KiB random-write IOPS：9.8k
    - 大块读：1.05 GiB/s
    - replicated write：607 MiB/s

#### L3 高可用：[kube-vip](https://github.com/kube-vip/kube-vip)

K8s API 和 LoadBalance Service 的 VIP 由 kube-vip 持有，提供 HA。

`externalTrafficPolicy` 只作用于外部流量进入集群的 Service(LoadBalancer/NodePort)，决定两件耦合的事：流量到达节点后转发给哪些 pod、是否保留客户端源 IP。

- Cluster(默认)：任何节点收到流量后，kube-proxy 可以 DNAT 给集群中任意 backend pod，包括跑在其他节点上的。若目标 pod 在别的节点，流量要再跨节点转发一跳；为了让回包能原路返回，kube-proxy 会把这类流量的源地址改写成节点 IP(SNAT)。代价就是 backend 看到的是节点 IP，客户端真实源 IP 丢失。好处是负载摊到所有副本，节点上没有 pod 也能服务。
- Local:只 DNAT 给本节点上的 pod。因为流量从网卡直接本机转发给本机 pod，来回路径对称，不需要 SNAT，客户端真实源 IP 得以保留；还省掉跨节点转发一跳。代价有两个：一是本节点没有该 Service 的 pod 时流量直接 DROP；二是 Kubernetes 会在每个节点开一个 healthCheckNodePort，没有本地 endpoint 的节点在这个健康检查端口上报告不健康，供 LB 绕开自己。

我们的需求如下：

- A：由于镜像站只有一个域名，又需要同时提供 HTTP/HTTPS 和 rsync 服务，因此多个 LoadBalancer Service（envoy-gateway 和 rsync-gateway）需要共享一个 VIP，但在不同端口上提供服务
- B：我们需要看到客户端的源 IP 以进行统计，因此这些 Service 都需要 `externalTrafficPolicy: Local`

kube-vip 官方支持需求 A 的方式是 common lease：两个 Service 打相同的 kube-vip.io/leaseName。但在这种情况下，kube-vip v1.2.3 要求 `externalTrafficPolicy=Cluster`，否则报错，这与我们的需求 B 冲突。kube-vip 该要求是出于保守考虑：common lease 可能会导致 VIP 在没有本地 endpoint 的节点上，流量被黑洞。

综上所述，我们采用的策略是：

- 将相关 service 全部部署成 DaemonSet，保证每个节点都有本地 endpoint，避免黑洞
- 让其中一个 Service 独占 kube-vip 管理，其余 Service 使用 `kube-vip.io/loadbalancerIgnore: "true"`，不再管理

长期来看更优雅的方式是 kube-vip 支持放宽 `externalTrafficPolicy=Local` 的要求，但该逻辑目前写死在 kube-vip 中，我们暂时采用上面的绕过方式。

此外，`externalTrafficPolicy != Cluster` 时，kube-vip 的租约范围限制在有本地 endpoint 的节点。所以对相关 workload 限制调度范围后，VIP 也会跟着被限制。

#### L4/L7 网关：[gateway-api](https://github.com/kubernetes-sigs/gateway-api)

[K8s Gateway API](https://gateway-api.sigs.k8s.io/) 有多种实现，其中 [Envoy Gateway](https://github.com/envoyproxy/gateway) 有较强的社区支持，也是我们最终的技术选型。

由于历史上镜像站的主要技术栈是 Nginx，所以我们初期是基于 [NGINX Gateway Fabric
](https://github.com/nginx/nginx-gateway-fabric) 的。从架构上来看，NGF 的设计已经足够尽力足够好，但它在 K8s 场景下就是显得不够原生。我们选择 Envoy 而不是 Nginx 的理由包括但不限于：IP 黑白名单、连接数限制、GeoIP、JWT 等功能涉及 NGINX Plus 商业订阅或者 Snippets 手写 Nginx 配置；而 Envoy 完全开源且内置这些支持。

Gateway API 能够方便地扩展协议。我们将 [ustclug/rsync-proxy](https://github.com/ustclug/rsync-proxy) 封装为 [ZJUSCT/rsync-gateway](https://github.com/ZJUSCT/rsync-gateway)，以在集群中通过 Gateway API 对 rsync 进行反代。

#### 配置自动更新：[Reloader](https://github.com/stakater/Reloader)

Secret 和 ConfigMap 变动时往往需要重启相应的 Workload，相关机制：

- Helm Chart 通过向 Deployment 等处注入 ConfigMap 的 Hash 来实现自动 Rollout，见 [Chart Development Tips and Tricks | Helm](https://helm.sh/docs/howto/charts_tips_and_tricks/#automatically-roll-deployments)。
- ArgoCD 自己通过 K8s API Watch 相关 Resource 的变化，自己不需要重启。

但手动编排的资源/existingSecret 等缺少类似机制。此时可以为其添加 Annotation `reloader.stakater.com/auto: "true"`。

#### DNS：[external-dns](https://github.com/kubernetes-sigs/external-dns)

自动根据集群内的服务设置 DNS 记录。

#### 证书：[cert-manager](https://github.com/cert-manager/cert-manager)

使用 DNS-01 或 HTTP-01 自动管理证书。

#### 容器镜像 Registry：[Harbor](https://github.com/goharbor/harbor)

搭配 [ZJUSCT/registry-gate](https://github.com/ZJUSCT/registry-gate)，提供容器镜像 Pull Through Cache。

## ArgoCD 与 GitOps

[ArgoCD](https://argo-cd.readthedocs.io/en/stable/) 是用于 K8s 的 GitOps CI/CD 工具。对于本仓库，它读取 `apps/` 下的 [Kustomization](https://kubectl.docs.kubernetes.io/references/kustomize/) 项目并将其部署到集群。

我们约定 Kustomization 项目的布局如下：

```text
argocd
├── .gitignore # 一般忽略 charts/*
├── charts
├── kustomization.yaml
├── resources
│   ├── apps.yaml
│   ├── configmap.yaml
│   ├── namespace.yaml
│   └── secret.yaml
└── values
    └── argo-cd-9.5.2.yaml
```

- Kustomization 总是将 Helm Chart 缓存到 `charts/` 下。由上游维护的 Helm Chart 一般不纳入本 Git 仓库。
- `helmCharts.repo` 应优先使用 OCI 地址，上游不提供 OCI 再考虑传统 HTTP Chart 仓库。OCI 可以按名称和版本直接拉取 Chart，避免下载整个仓库索引、拖慢 ArgoCD 生成 manifest。
- `values/` 下的文件应当从 `charts/` 中具有完整默认值的 `values.yaml` 复制而来，然后根据实际情况修改。这是为了给 AI 提供更多的上下文信息，也方便对比默认值。这一点也约束接下来要介绍的「更新流程」。

应用的更新流程（一般由 AI 辅助）：

1. 检查上游 Helm Chart 版本是否有更新。如果有更新：

    - 记录当前 value 文件和对应默认 value 文件的 diff。
    - 修改 kustomization.yaml 中的 Helm Chart 版本号，拉取新 Chart。

2. 对比新旧 Chart 的默认 value 文件。

    - 如果上游有重要变更（例如架构变更、`values.yaml` 大幅重构导致变化过多等难以处理等情况），向用户报告。
    - 拷贝新的默认 `values.yaml`，然后按照上一步的 diff 进行修改，生成新的 value 文件。

3. 用户负责审核与提交。

其他：

- 可以通过移除 Application 的 `spec.syncPolicy.automated` 或者添加 `automated.enabled: false` 来暂停 ArgoCD 对该应用的自动同步，用于临时绕过 GitOps。
- 使用 `argocd.argoproj.io/refresh: "hard"` Annotation 强制刷新应用。
- 手动生成 K8s 资源：在相应目录下运行

    ```bash
    kubectl kustomize --load-restrictor LoadRestrictionsNone --enable-helm .
    ```

- 手动部署 K8S 资源：要求使用 server-side apply

    ```bash
    kubectl kustomize --load-restrictor LoadRestrictionsNone --enable-helm . | kubectl apply --server-side --force-conflicts=true -f -
    ```

TODO：解释 SSA 和处理事项

- 临时修改 Argo CD 管理的资源时，必须注意 server-side apply 的字段所有权。SSA 只会删除同一 field manager 先前拥有、但本次 apply 已省略的字段；由临时 manager 写入的字段不会因为 Git 中已删除而自动消失，Argo CD 甚至可能仍显示 `Synced`。Agent 或人工排障结束前必须：

    1. 记录临时 manager 修改过的精确字段路径；
    2. 使用 JSON Patch 等方式只删除这些临时字段，不要为了清理而替换整个资源；
    3. 确认 Git manager 已拥有所有应保留字段后，让原临时 manager apply 仅含 `apiVersion`、`kind`、`metadata.name` 和 `metadata.namespace` 的 identity-only 清单，以释放其余共用字段的所有权；必须先用 `--dry-run=server` 确认操作前后 `spec` 完全一致；
    4. 对比 Git 渲染结果与 live `spec`，并通过 `kubectl get ... --show-managed-fields` 确认临时 manager 已消失；
    5. 确认控制器已观察到新 generation、下游 Workload 已重新生成，且 Argo CD 仍为 `Synced/Healthy`。

    不要把 `--force-conflicts` 当作常规清理手段；它会转移清单中所有重叠字段的所有权，容易覆盖其他控制器或 Argo CD 的修改。对于应从期望状态中消失的单个字段，优先执行精确的 JSON Patch `remove`。字段删除后无需让 Argo CD“拥有不存在的字段”；将来若 Git 再次声明该字段，Argo CD 会自然取得其所有权。

## 镜像站的工作原理

### 镜像同步管理器：[Falcon](https://github.com/ZJUSCT/falcon/)

镜像站的基础设施十分多样，也因此诞生了非常多镜像同步管理器，例如：

- [tuna/tunasync](https://github.com/tuna/tunasync)
- [sjutg/lug](https://github.com/sjtug/lug)
- [ustclug/Yuki](https://github.com/ustclug/Yuki)
- [PKUOSC/SyncController](https://github.com/PKUOSC/SyncController)
- [ZJUSCT/MirrorManager](https://github.com/ZJUSCT/MirrorManager)（第二代 ZJU Mirror 使用的镜像同步管理器）

第三代 ZJU Mirror 使用的同步管理器是 [Falcon](https://github.com/ZJUSCT/falcon/)，详细信息请移步相应仓库。

同步管理器的基础功能是：管理、调度下文将介绍的各种同步、服务，展示镜像状态等。

### 同步卷根目录的属主

zfs-localpv 新建 PVC 的根目录默认由 root 持有。`fsGroup` 可以提供组写权限，但非 owner 仍不能设置根目录的任意 mtime，rsync 会报 `failed to set times ... Operation not permitted`。

所有 Mirror 的 sync Pod 都先运行 `init-sync-volume`，通过共享 ConfigMap 中的 [init-sync-volume.sh](apps/mirror-production/configs/init-sync-volume.sh) 仅修正 `/data` 根目录的 owner。它不递归修改内容、不调整 group/mode；ftpsync 的锁清理在此之后执行。初始化容器以 UID 0 运行，丢弃所有能力后仅添加 `CHOWN`；实际同步容器仍以非 root 身份运行。发布 Pod 不运行此初始化。

生成配置使用 `sync.uid` 指定同步 UID，默认 65532，QFM 默认 65432；同一数值同时用于同步容器和初始化容器的 `SYNC_UID`。手工维护的 Mirror 也必须保持这两者一致。QFM 的发布 UID 继续为 65532，以保持 bitflip 的读权限隔离。

此初始化只解决新卷根目录的属主问题，不修复已有子目录的错误属主，也不能替代既有数据的 UID 迁移。切勿将递归 `chown` 加入每轮同步；大镜像的全树扫描代价高，还可能破坏已有权限安排。

### 同步工具：[rsync](https://github.com/RsyncProject/rsync)

绝大部分镜像使用 rsync 或其变种进行同步。

ZJU Mirror 默认添加的 rsync 参数：

- **`-a`（-rlptgoD）**：归档模式：递归、符号链接、权限、mtime、属组属主、设备文件。普遍适用于各类同步任务。
- **`-H`（硬链接）**：发行版仓库大量用硬链接去重（同一文件在 pool/ 与 dists/ 间共享 inode），不传 `-H` 会把硬链接拆成独立文件，容量翻倍且失去上游的存储结构。
- **`--no-o --no-g`**：不保留上游 owner/group。当 rsync 不以 root 运行时，默认为 `--no-o --no-g`，这里显式声明，以从 `-a` 中排除。
- **`--stats -h`**：输出传输统计到 Job 日志。
- **`--itemize-changes`**：输出每个文件的变化，便于排查。
- **`--partial-dir=.rsync-partial`**：启用 rsync 断点续传，保留部分文件在 `.rsync-partial`。rsync 默认中断即删除临时文件。
- **`--filter=P .rsync-partial/`**：protect 规则，与 `--delete-excluded` 配套必需：`--partial-dir` 指定的目录会被 rsync 隐式 exclude，而 `--delete-excluded` 恰会删除接收端被 exclude 的路径。没有这条保护，断点续传的半成品会在下次同步被一并删掉。
- **`--exclude .~tmp~/`**：`.~tmp~` 是 rsync 的接收端临时目录约定。上游镜像站自己同步时会把传输中的文件放在这里。
- **`--delete`**：删除上游已消失的文件。
- **`--delete-excluded`**：让接收端匹配 exclude 规则的路径也参与删除，主要用于清理残留，例如从老站点拿来的初始同步数据可能有被 exclude 的内容，如果不设置该选项，这些内容就会被一直留着，并导致 rsync 报 `cannot delete non-empty directory`。
- **`--safe-links`**：忽略指向目录树**外**的符号链接。安全项：防止上游（或被入侵的上游）用 symlink 逃出 `/data`。
- **`--timeout=120 --contimeout=120`**：I/O 停滞 120 秒或连接 120 秒失败即退出，防止卡死。
- **`-6`**：强制 IPv6。如果上游有 IPv6 则应当添加此选项。

ZJU Mirror 默认不使用的参数：

- **`--delay-updates` / `--delete-after`**：已经通过快照实现了原子发布，不需要这些，换来更少的临时空间占用和更简单的同步流程。
- **`--sparse`**：ZFS 已启用压缩。
- **`--checksum`**：要求服务端对整个文件集合计算校验和，一般 size+mtime 判定已足够。仅特定情况临时用于排查。

需要认证的 rsync 上游沿用现有约定：用户名写入 `info.upstream` URL，
`sync.rsync.password_secret` 引用同命名空间 Secret 的 `RSYNC_PASSWORD` 键。
用户名随上游 URL 公开，密码只通过环境变量交给 rsync，不写入仓库明文。

### 同步工具：[ftpsync](https://salsa.debian.org/mirror-team/archvsync)

Debian 及其衍生发行版一般使用 ftpsync 同步，它基于 rsync 设计了两阶段同步，要点如下：

- 两个标记文件：`Archive-Update-Required-<name>`（简称 AUR）表示同步需要再次运行。`Archive-Update-in-Progress-<MIRRORNAME>`（简称 AUIP）写 ftpsync 自己的 PID。
- 完整的同步过程：
    - 创建 AUR 和 AUIP 标记
    - Stage 1：rsync 同步元数据索引外的一切，包括上面两个标记
    - Stage 2：
        - 如果扫到不是自己的 AUIP，则说明 Stage 1 时上游正在同步。移除 AUIP 后 Sleep 一段时间重新启动 Stage 1。最多重复 3 次，仍然扫到 AUIP 则报错退出。
        - 执行完整 rsync 同步
    - 删除 AUR 和 AUIP 文件

ftpsync 的一个缺点是：所有日志总是重定向到文件，逻辑写死在相关脚本中，没有可配置的余地。在集群中，我们统一通过容器的 std 输出收集日志，因此对 ftpsync 做 Patch，见 [containers/archvsync](containers/archvsync)。

### 同步工具：[quick-fedora-mirror](https://pagure.io/quick-fedora-mirror)

Fedora 及其衍生镜像一般使用 quick-fedora-mirror 同步。它是一个 zsh 脚本，通过文件清单机制减小 rsync 对 server 侧带来的压力：

- server 侧由 create-filelist 为每个模块生成 fullfiletimelist-<module>（记录每个
  文件 mtime/ctime 较新者与大小，并附 repomd.xml 等不变名文件的校验和）；
- client 下载清单并与本地对比，将新增/更新/尺寸变化/校验和不符的文件合并为一份
  --files-from 列表，交给单次 rsync（-aSH --delay-updates）；
- 文件列表阶段从十小时级降到秒级，因此可以高频轮询（官方称可至 10 分钟一轮）；
- 删除在传输完成后按清单执行（类似 --delete-delay）；单次传输使跨模块硬链接得以
  保留。

Fedora 和相关镜像采用独特的 bitflip 发布机制：

- 发布前内容以 0750 预置，flip 后 0755；
- 官方要求同步用户与服务用户分离，避免预置内容提前可读

quick-fedora-mirror 在同步时使用二级目录 `fedora/*`。我们为同步 Pod 保持该原生布局，但发布 Pod 直接挂载 subPath。

### 同步工具：[shadowmire](https://github.com/taoky/shadowmire)

shadowmire 由 USTC 镜像站成员开发，是 PyPI 官方同步工具 [bandersnatch](https://github.com/pypa/bandersnatch) 的替代品，解决了后者的一些问题：

- 无法清理上游已删除的包
- 未对异常包（例如 [uselesscapitalquiz](https://pypi.org/project/uselesscapitalquiz/)）做过滤

### 同步工具：[tsumugu](https://github.com/taoky/tsumugu)

tsumugu 由 USTC 镜像站成员开发，用于同步 HTTP(S) 类型的上游目录，例如 docker-ce、postgresql、repo.anaconda.com。它解决了其它工具的痛点：

- `lftp mirror` 顺序爬取目录，实测约 8 对象/秒，几十万文件量级一轮要一天以上；
- `rclone`（http backend）对每个文件发一次 HEAD 获取 size/mtime，64 万文件即 64 万 + 次请求/轮；
- `wget -m` 不传播删除，且同样逐文件发条件请求。

工作原理：

- 递归抓取并解析上游目录列表页（内置 nginx、Apache、fancy-index 等多种 parser），**只从列表读取 size/mtime** 做增量判定，无逐文件 HEAD，每轮固定开销 = 目录数次 listing 请求；
- 仅对新增/变更文件发起 GET，用下载响应的 `Last-Modified` 头把秒级 mtime 落盘（列表页时间戳只有分钟精度）；
- 列表页解析或拉取失败时**拒绝执行删除**（fail-safe），另有 `--max-delete`（默认 100）与 `--no-delete` 删除保护；
- 同一二进制含 `sync`（同步）与 `list`（仅列清单）两个子命令，支持 `--threads`、`--dry-run`、`--exclude/--include`（正则）、`--user-agent`、重试等。

使用要点：

- 典型调用：`tsumugu sync --parser nginx --threads 4 --max-delete 5000 <upstream> <local>`；
- 生成器使用 `sync.type: tsumugu`，参数置于 `sync.tsumugu`（`parser`、`threads`、`max_delete`、`extra_args`），上游地址记录在 `info.upstream`；
- `containers/tsumugu` 构建时安装最新上游版本；同步 Pod 使用 `ghcr.io/zjusct/tsumugu:latest` 和 `imagePullPolicy: Always`；
- PostgreSQL 镜像完整 `/pub/` 树；SRPM 子树需要 `s3-indexbuilder` parser override，三个已失效的历史 SRPM 目录明确 exclude。不要以全局忽略 HTTP 错误替代这些规则；只有完整同步成功，Falcon 才会发布新快照；
- 实测：PostgreSQL 官方树（64 万文件 / 12,940 目录 / 800 GB）一轮全量 listing 扫描 4 分 53 秒（threads 6）。

### 同步工具：[git](https://github.com/git/git)

TODO

### 特殊镜像：crates 系列

TODO

`crates.io-index`：

- 稀疏索引：分片小文件树（1/、2/、3/、a-…，每 crate 版本一个 JSON 行文件）。cargo ≥1.68（2023-03 起默认）按需 GET 单文件

`crates.io-index.git`：

- 同一索引的 git 仓库形态，供老 cargo（git 协议）与要全量历史的工具
- 上游：`github.com/rust-lang/crates.io-index.git`

`crates.io`：

- 静态包体：crates/<名>/<名>-<版本>.crate tarball。
- 上游：`static.crates.io`

下载流程：

- cargo 从 `crates.io-index` 拿 `config.json`，读 `dl` 决定 tarball 从哪下

同步流程：

### HTTP 服务：nginx

使用标准 [`nginxinc/nginx-unprivileged`](https://hub.docker.com/r/nginxinc/nginx-unprivileged)。均使用 `mainline-alpine-otel`。共享 Nginx 配置固定使用两个 worker；默认使用较低的 request，所有档位统一设置 4 CPU 的安全上限，并按热度设置不同的内存上限：

| Workload Tier | Worker | CPU Request | CPU Limit | Memory Request | Memory Limit |
| --- | ---: | ---: | ---: | ---: | ---: |
| Small | 2 | 10m | 4 | 32Mi | 256Mi |
| Standard | 2 | 10m | 4 | 32Mi | 1Gi |
| Hot | 2 | 10m | 4 | 32Mi | 2Gi |

CPU request 用于调度，并在节点发生 CPU 争用时提供最小权重。两个 worker 使正常请求处理的 CPU 并行度约为 2；统一的 4 CPU limit 不应位于正常工作边界上，主要用于限制漏洞利用、异常线程或额外进程对单个节点的影响。内存 limit 用于隔离异常连接、突发流量或程序缺陷，避免单个 Nginx 实例耗尽节点内存。`Small` 档仍适合数量多、常态访问量很低的冷镜像。CPU limit 不能替代 Envoy 层的连接数、请求速率和并发保护；分布式攻击仍可能同时压满多个 Pod。

对于超热门镜像，设置更多副本。

至于其他 HTTP Server：我们曾经对比测试过 Caddy 的性能，与 Nginx 仍有较大差距。

### [smart HTTP](https://git-scm.com/book/en/v2/Git-on-the-Server-Smart-HTTP)（Git）服务：[git-http-backend](https://git-scm.com/docs/git-http-backend)

下列镜像使用 git-http-backend 提供 smart HTTP 服务：

```text
crates-io
```

目前我们采用 Nginx + git-http-backend 的简单组合。部分镜像站添加了排队等功能，我们后期可考虑采用：

- [sjtug/mirror-docker-unified/git-backend](https://github.com/sjtug/mirror-docker-unified/tree/main/git-backend)
- [ustclug/git-queue](https://github.com/ustclug/git-queue)

### Rsync 服务：rsyncd

## 如何维护本仓库的镜像

### 镜像信息约定

镜像由 Falcon 的 `Mirror` CR 描述；同步、缓存和代理模式共用该类型。字段定义与模式说明见 Falcon 仓库。

确保查询的是官方信息。如果查不到，应如实报告。主要关注：

- 合适的同步上游。由于 CERNET 内 TUNA、USTC 等服务器压力较大，NJU 同步质量不佳等原因，所以我们更加偏好官方的上游，能选官方尽量选官方。也需要看看上游的 rsync MOTD、module 信息等，这里有时也有不少信息。
- 官方建议的同步间隔。如果官方有建议，那我们就应当将同步间隔设为对应值。例如，上一轮查到 almalinux 同步间隔应当为 3h，我们就改为 3h。并且一般 timeout 和 interval 设置为相同的值。
- 镜像的描述（info.description）也可以帮我优化下，应该是简短的、精炼的描述，老的描述写得并不是很好。最好是以官方自己怎么介绍该镜像为准。

#### 模板生成的镜像

`apps/mirror-production/mirrors/` 存放手工维护的简化源配置，每个 YAML 文件描述一个镜像。`gen-mirrors.py` 读取这些配置，结合 `snippets/` 中的模板，将完整的 `Mirror` CR 和 `kustomization.yaml` 写入 `mirrors-generated/`。不要手工修改生成文件。

修改源配置或模板后，在 `apps/mirror-production/` 下执行：

```sh
make                     # 重新生成 mirrors-generated/
./gen-mirrors.py --check  # 检查源配置与生成结果是否一致
```

提交时同时包含源配置或模板的修改，以及对应的生成文件。

`mirrors/<name>.yaml` 中的 `comment` 字段记录官方政策和上游调研信息，例如：

```yaml
comment:
  official:
    docs:
      - https://archlinux.org/
      - https://wiki.archlinux.org/title/DeveloperWiki:NewMirrors
      - https://archlinux.org/mirrors/
    policy:
      - 同步间隔不得短于 1 小时，并且至少每日同步一次。
      - Tier 1 从官方 Tier 0 同步，并向其他镜像提供 rsync 服务。
      - Tier 2 从 Tier 1 同步，面向最终用户提供下载服务。

  upstreams:
    - url: rsync://rsync.mirrors.ustc.edu.cn/archlinux/
      stack: <ipv6|ipv4|dual>
      surveyed_at: 2026-09-14
      status: selected
      metrics: IPv4 RTT 23ms. IPv6 RTT 15ms, 171MiB/s
      note: Tier 1，CERNET 内路径较短，IPv4 和 IPv6 均可用。

    - url: rsync://rsync.archlinux.org/archlinux/
      stack: <ipv6|ipv4|dual>
      surveyed_at: 2026-09-14
      metrics: IPv4/IPv6 RTT 约 234ms、171MiB/s
      note: Tier 0，官方仅允许 Tier 1 镜像使用。
```

#### 手动编写的镜像

无法由通用模板表达的镜像放在 `apps/mirror-production/mirrors-manual/`，手工维护。

### 安全约定

- Pod：

    ```yaml
    securityContext:
      runAsNonRoot: true
      runAsUser: 65532
      seccompProfile:
        type: RuntimeDefault
    ```

- Container：

    ```yaml
    securityContext:
      allowPrivilegeEscalation: false
      capabilities:
        drop: [ALL]
      readOnlyRootFilesystem: true
    ```

### 部署与验证约定

集群只保留 `mirror-production` 一个 Falcon 实例，对外服务域名为 `mirrors.zju.edu.cn`、`mirror.zju.edu.cn`。

Falcon 的 `Mirror` CRD 定义是集群级资源，`Mirror` 实例位于各自的命名空间。不同命名空间中的实例共享同一份 schema，无法通过同集群的测试实例隔离 CRD 升级。新版 Falcon 先运行本地 `make check`，再通过 `make e2e` 在独立 kind 集群中验证；发布前等待分支 CI 通过，再推送版本 tag，由 GitHub Actions 构建镜像和 Chart。

生产升级前检查 CRD 字段变化、现有 CR 迁移以及回退方案，协调更新 CRD、控制器和镜像配置；升级后验证同步、快照、发布、路由与 MirrorZ 输出。新镜像的同步和服务配置也应先完成验证，再纳入生产配置。

### 可观测性

- 指标：Prometheus 保留 48 小时本地缓冲，通过 remote_write 写入 Mimir；Mimir 在 Ceph 对象存储保留 180 天，作为 Grafana 默认指标源。
- 链路：OTel collector 写入 Tempo，Ceph 对象存储保留 180 天。
- 日志：网关 access log 经 gateway collector、节点容器日志经 node-logs → aggregator collector 写入 ClickHouse `otel.otel_logs`，TTL 为 180 天。ClickHouse 使用 ceph-block 2Ti PVC；Loki 已完全下线。
- Grafana 的 ClickHouse 数据源使用只读 `app` 用户，collector 使用 `otelcollector` 用户；跨命名空间凭据由各自的 SealedSecret 注入。日志查询入口为 Explore 和 Infrastructure 文件夹内的 **Gateway Traffic** dashboard，可选择 Production、Staging 或全部网关；Staging 网关仍承载 Falcon、registry 等站点，与已移除的 staging 镜像实例不同。
- Dashboard ConfigMap 用 `k8s-sidecar-target-directory` 指定目录；Grafana provider 必须开启 `foldersFromFilesStructure`，例如 Mimir mixin 的 27 个 dashboard 放入 **Mimir Dashboards**。

### 镜像 e2e 可用性测试

推荐在添加镜像时，在 `tests/mirrors-e2e/` 下为其维护一份对应的 e2e 测试，用来验证镜像是否能够正常工作。

对于大部分镜像来说，e2e 测试的流程为：

| 步骤 | 以 APT 为例 |
| --- | --- |
| 更新索引 | `apt update` |
| 随便找一个包装上 | `apt install $(random package)` |

### 一些上游经验

- mirrors.yandex.ru：不好用
    - 线路绕路欧洲，甚至比不上美国
    - rsync 临时文件没有好好处理，经常出现 [sender] send_files failed to open "/releases/ppc/autobuilds/20260916T034558Z/.stage3-power9le-desktop-systemd-20260916T034558Z.tar.xz.BMMFnM" (in gentoo-distfiles): Permission denied (13) 等错误

### 镜像间的子集关系

对于子集关系的镜像，我们只同步更完整的集合，子集通过父镜像 `publish.aliases` 中的**子集 alias** 对外提供：数据、同步与发布完全复用父镜像，网关将子集路径 301 到父镜像规范路径下的对应子目录，子集同时以独立 cname 进入 `mirrorz.json`（status 投影父镜像）。以下是 `mirrors/debian-cdimage.yaml` 中的配置片段：

```yaml
metadata:
  name: debian-cdimage
publish:
  aliases:
    # 普通 alias（字符串简写）只做路径别名，如大小写：- /CDIMAGE
    - path: /debian-nonfree
      subset:
        subpath: unofficial/non-free   # 镜像数据内的相对路径
        cname: debian-nonfree          # 缺省取 path 去首 /
        description: Debian 含非自由固件组件的安装镜像
        upstream: rsync://cdimage.debian.org/cdimage/unofficial/non-free/
  http: ...
```

当前的子集关系：

- `debian-nonfree` -> `debian-cdimage/unofficial/non-free`
- `debian-cd` -> `debian-cdimage/release`
- `kernel` -> `kernel.org/linux/kernel`

注意两点：

- 子集路径指向的子树必须真实位于父镜像的同步范围内。`debian-cd` 已与 `debian-cdimage/release` 合并，由父镜像统一同步和发布。
- 语义与机制细节见 Falcon 仓库 README 的「别名与重定向」。
