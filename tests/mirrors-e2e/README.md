# mirror-e2e

ZJU 镜像站各镜像的端到端测试集合。每个子目录对应一个镜像站：一个 `Dockerfile`
（官方客户端镜像 + 测试入口）+ 一个 `e2e.sh`（测试流程）。包管理器类镜像的通用
流程：元数据刷新 -> 随机选一个包安装 -> 可执行冒烟。

镜像站地址统一使用 `http://$MIRROR_HOST`，默认域名为 `mirrors.zju.edu.cn`，
用于验证纯 HTTP 兼容性。外部上游的密钥、引导工具等仍按其官方 HTTPS 地址获取；
包签名和校验和验证保持不变。Debian 测试禁止 APT 跟随重定向，防止静默升级
HTTPS 后误判 HTTP 可用；PyPI 测试通过 `--trusted-host` 显式允许指定域名的 HTTP 索引。

## 用法

```sh
export MIRROR_HOST=mirrors.zju.edu.cn
make test-homebrew                # 或 docker compose run --rm homebrew
make test-debian
make test-pypi
make test-anthon
make test-openkylin
make test-archlinux
make test-ubuntu
make test-centos / test-centos-vault / test-centos-stream
make test-ubuntu
make test-cpan
make test-ctan
make test-cran
make test-armbian
make test-rocky
make test-gentoo
make test-qt
make test-debian PKG=curl         # 指定包（默认随机）
make test-pypi MIRROR_HOST=mirror.zju.edu.cn    # 指定其他待测域名
make clean
```

## 各服务覆盖的镜像路径

| 服务 | 客户端 | 元数据 | 包本体 |
|---|---|---|---|
| homebrew | brew（官方镜像） | `HOMEBREW_API_DOMAIN` → `/homebrew-bottles/api`；`HOMEBREW_*_GIT_REMOTE` → `/homebrew/*.git` | `HOMEBREW_BOTTLE_DOMAIN` → `/homebrew-bottles`（flat + OCI） |
| debian | apt（stable-slim） | apt `sources` → `/debian`（Release/InRelease 签名校验） | 同一 apt 会话 |
| pypi | pip（python:slim） | pip `index-url` → `/pypi/web/simple` | `/pypi/web/packages` |
| anthon | oma（AOSC 官方容器） | `/etc/apt/sources.list` → `/anthon/debs` | 同一 oma 会话 |
| openkylin | apt（官方 3.0 容器） | apt `sources` → `/openkylin`（huanghe 套件） | 同一 apt 会话 |
| archlinux | pacman（官方 base 容器） | mirrorlist → `/archlinux/$repo/os/$arch`（db/包签名经 archlinux-keyring 校验） | 同一 pacman 会话 |
| ubuntu | apt（官方 24.04 容器） | apt `sources.list` → `/ubuntu`（Release/InRelease 签名校验） | 同一 apt 会话 |
| centos-vault | yum（官方 centos:7 容器） | yum repo → `/centos-vault/7.9.2009`（repomd 签名校验） | 同一 yum 会话 |
| centos-stream | dnf（官方 stream9 容器） | dnf repo → `/centos-stream/9-stream`（repomd 签名校验） | 同一 dnf 会话 |
| centos | 结构验证（alpine+curl） | 骨架工件 `/centos/{TIME,timestamp.txt,…}` 全 200（TUNA 布局下该模块为中空骨架，包内容在 centos-vault，见 CR 头部） | 无（无包内容） |
| cpan | cpan/cpanm（官方 perl 容器） | CPAN urllist → `/cpan`（01mailrc/02packages 索引） | 同一 CPAN 会话 |
| ctan | tlmgr（官方 TeX Live 容器） | `tlmgr option repository` → `/ctan/systems/texlive/tlnet`（tlpdb） | 同一 tlmgr 会话 |
| cran | R（官方 r-base 容器） | `install.packages` repos → `/cran`（PACKAGES 索引） | 同一 R 会话 |
| armbian | apt（Debian arm64 容器 + qemu） | apt `sources.list` → `/armbian`（InRelease 签名校验） | 同一 apt 会话 |
| rocky | dnf（官方 9 容器） | repo `baseurl` → `/rocky/9/BaseOS`（repomd 签名校验） | 同一 dnf 会话 |
| gentoo | wget（复刻 emerge-webrsync 语义） | portage 快照下载 + md5sum 校验 → `/gentoo/snapshots` | 快照级 |
| qt | wget（在线安装器） | 安装器下载 + 尺寸对账 → `/qt/official_releases` | 安装器级 |
| manjaro | pacman（archlinux base 容器，与 manjaro 仓库格式同源） | pacman.conf → `/manjaro/stable/{core,extra,community,multilib}`（SigLevel=Never，manjaro 密钥环 arch 容器不可用） | db 内 SHA256 对账 + zstd/tar 结构冒烟（跨发行版安装不可靠） |
| msys2 | pacman（archlinux base 容器，与 msys2 仓库格式同源） | pacman.conf → `/msys2/{mingw/ucrt64,msys/x86_64}`（SigLevel=Never，msys2 密钥环 Linux 容器不可用） | db 内 SHA256 对账 + zstd/tar 结构冒烟（msys2 包为 Windows PE，无法在 Linux 安装执行） |
| deepin | 结构验证（alpine+curl） | `Release` 内 SHA256 → `/deepin/dists/apricot` 的 Packages.gz 对账（deepin 无官方客户端容器，GPG 校验链缺锚点） | 索引包 Filename/Size 与 HEAD Content-Length 对账 |
| deepin-cd | 结构验证（alpine+curl） | 最新版本目录 → `/deepin-cd/<ver>/amd64/SHA256SUMS` 覆盖检查 | ISO HEAD Content-Length 与目录列表/清单对账（ISO 数 GB 不做全量下载） |
| elrepo | dnf（官方 rockylinux:9 容器） | `elrepo-release` 从镜像引导（--nogpgcheck 引入 GPG key），repo `baseurl` → `/elrepo/elrepo/el9/x86_64`（repomd/包签名经 elrepo key 校验） | 同一 dnf 会话装 kmod 包（依赖的 depmod/weak-modules 由 BaseOS 提供，Rocky 仓库保留） |
| bioconductor | R + BiocManager（官方 r-base 容器） | `BioC_mirror` → `/bioconductor`（BiocManager 按 R 版本解析 `packages/<ver>/bioc`；BiocManager 本体 bootstrap 自官方 CRAN） | 同一 R 会话装 BiocGenerics |
| docker-ce | apt（stable-slim） | GPG key 官方 download.docker.com 引导 → `docker-ce/linux/debian`（Release/InRelease 签名校验） | 同一 apt 会话装 docker-ce-cli |
| kali | apt（官方 kali-rolling 容器，自带密钥环） | 清空自带 sources.list.d 后 sources.list → `/kali`（签名校验） | 同一 apt 会话随机装小包 |
| ros2 | apt（官方 ubuntu:24.04 容器） | GPG key 官方 rosdistro ros.key 引导 → `/ros2/ubuntu` noble（签名校验） | 同一 apt 会话装 ros-jazzy-ros-workspace |
| rustup | rustup-init（stable-slim） | rustup-init 官方引导 + 与镜像逐字节 cmp；`RUSTUP_DIST_SERVER` → `/rustup` | minimal 工具链经镜像 + cargo 编译运行 |
| gnu | 结构+签名验证（alpine+gpgv） | 官方 gnu-keyring.gpg 引导 → `/gnu/bash` 源码包 `.sig` GPG 校验 | tar 结构冒烟 |
| llvm-apt | apt（stable-slim） | GPG key 官方 apt.llvm.org 引导 → `/llvm-apt/trixie`（签名校验） | 同一 apt 会话装 clang + 编译运行 |
| mozilla | apt（stable-slim） | GPG key 官方 packages.mozilla.org 引导 → `/mozilla/apt`（suite 为 mozilla；签名校验） | apt-get download firefox + dpkg-deb 元数据 |
| linuxmint | apt（官方 ubuntu:24.04 容器） | 官方 linuxmint-keyring deb 引导（dearmor 后 signed-by）→ `/linuxmint`（noble 系 codename 动态解析） | apt-get download mint-* 包 |
| proxmox | apt（stable-slim） | GPG key 官方 download.proxmox.com 引导（本网络证书异常时回退镜像同源副本）→ `/proxmox/debian/pve` bookworm（签名校验） | apt-get download pve-manager |
| kali-images | 结构验证（alpine+curl） | `kali-weekly/` SHA256SUMS 覆盖检查 | ISO HEAD Content-Length 与列表对账 |

通过标准：脚本末尾打印 `E2E PASS`。homebrew 另要求无 ghcr.io 回落。
注意：客户端静默回落检测不到，最终凭据以镜像站 publish access log 为准。

## 各镜像容器化的注意事项（踩坑记录）

- debian / openkylin 官方容器均**不带 ca-certificates**；测试直接使用 HTTP，
  不再额外拷入 CA bundle 或补建 OpenSSL 信任路径，以覆盖无 CA 的精简容器。
  生产域名 `mirror(s).zju.edu.cn` 不强跳 HTTPS，历史上为 308 跳转添加的
  CA 注入不再需要。
- anthon 用的 AOSC 容器自带 tree/jq/bc/cpio（oma 判定“已安装”而不下载），
  随机池需选容器中不存在的小包。
- elrepo 2025 年起改用 v2 GPG key 签包，`elrepo-release` 同时安装新旧两把
  （`RPM-GPG-KEY-elrepo.org`、`RPM-GPG-KEY-v2-elrepo.org`）；repo 的 `gpgkey`
  只写旧 key 会 GPG check FAILED，须两把都列。
- rockylinux:9 自带 `curl-minimal`，再 `dnf install curl` 会与其文件冲突
  （提供同一路径），直接用自带的 curl 即可。
- 测试脚本里 `set -e` 会被 `cmd | tail` 管道吞掉退出码，失败也打印 PASS——
  校验步骤要么不用管道，要么先落盘再显式判断（rustup/ros2/mozilla 均踩过）。
- alpine 的 gpg 默认 keyboxd 会忽略 `--keyring` 自定义文件，纯校验场景用
  `gpgv --keyring`（gnu 测试）。
- linuxmint-keyring deb 自带的 `.gpg` 是 ASCII 盔甲多块格式，signed-by 需
  `gpg --dearmor` 后使用；docker 内 `_apt` 用户建临时文件失败会误报
  "repository is not signed"，测试容器用 `-o APT::Sandbox::User=root`。
- proxmox trixie 的 InRelease 由 2025 轮换的新 key 签署，keyserver 裸 key
  过不了 debian 13 sqv 绑定校验，e2e 改用 bookworm 套件（download-only）。

## 收录的已发现问题

- pypi：pip 的 Accept 头含 `text/html`，命中目录列表协商会拿到 mirror-front
  壳页而非 simple 索引——已由 pypi 专属 nginx 片段修复（见
  `apps/mirror-production/mirrors-manual/pypi.yaml` 的 `simple-index.conf`，
  待部署后 `make test-pypi` 验收）。
- pypi：对外 URL 原为无 `/web` 层的 `/pypi/simple`（发布容器以 subPath 直挂
  `web/`），与 mirrorz 帮助页及各兄弟站的 `…/pypi/web/simple` 约定不符。现已
  改为按 bandersnatch 根目录布局挂载，内容位于 `/pypi/web/` 下（根目录随其他
  站惯例原样暴露，无 `/web` 层的旧 URL 不再保留）。
