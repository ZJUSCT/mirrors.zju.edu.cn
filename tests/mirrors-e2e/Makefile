MIRROR_HOST ?= mirrors.zju.edu.cn
PKG ?=

.PHONY: test-homebrew test-debian test-pypi test-anthon test-openkylin test-archlinux test-ubuntu test-openeuler test-rosdistro test-fedora test-msys2 test-deepin test-deepin-cd test-elrepo test-bioconductor test-docker-ce test-kubernetes test-kali test-ros2 test-rustup test-manjaro test-gnu test-llvm-apt test-mozilla test-linuxmint test-proxmox test-kali-images test-immortalwrt test-packman test-raspberrypi test-raspbian test-ros test-termux clean

test-homebrew:
	docker compose build homebrew
	MIRROR_HOST=$(MIRROR_HOST) PKG="$(PKG)" docker compose run --rm homebrew

test-debian:
	docker compose build debian
	MIRROR_HOST=$(MIRROR_HOST) PKG="$(PKG)" docker compose run --rm debian

test-pypi:
	docker compose build pypi
	MIRROR_HOST=$(MIRROR_HOST) PKG="$(PKG)" docker compose run --rm pypi

test-anthon:
	docker compose build anthon
	MIRROR_HOST=$(MIRROR_HOST) PKG="$(PKG)" docker compose run --rm anthon

test-openkylin:
	docker compose build openkylin
	MIRROR_HOST=$(MIRROR_HOST) PKG="$(PKG)" docker compose run --rm openkylin

test-archlinux test-ubuntu test-openeuler test-rosdistro:
	docker compose build archlinux
	MIRROR_HOST=$(MIRROR_HOST) PKG="$(PKG)" docker compose run --rm archlinux

test-ubuntu:
	docker compose build ubuntu
	MIRROR_HOST=$(MIRROR_HOST) PKG="$(PKG)" docker compose run --rm ubuntu

test-fedora:
	docker compose build fedora
	MIRROR_HOST=$(MIRROR_HOST) PKG="$(PKG)" docker compose run --rm fedora

test-openeuler:
	docker compose build openeuler
	MIRROR_HOST=$(MIRROR_HOST) PKG="$(PKG)" docker compose run --rm openeuler

test-rosdistro:
	docker compose build rosdistro
	MIRROR_HOST=$(MIRROR_HOST) docker compose run --rm rosdistro

test-cpan:
	docker compose build cpan
	MIRROR_HOST=$(MIRROR_HOST) docker compose run --rm cpan

test-ctan:
	docker compose build ctan
	MIRROR_HOST=$(MIRROR_HOST) docker compose run --rm ctan

test-cran:
	docker compose build cran
	MIRROR_HOST=$(MIRROR_HOST) docker compose run --rm cran

test-armbian:
	docker compose build armbian
	MIRROR_HOST=$(MIRROR_HOST) docker compose run --rm armbian

test-centos:
	docker compose build centos
	MIRROR_HOST=$(MIRROR_HOST) docker compose run --rm centos

test-centos-vault:
	docker compose build centos-vault
	MIRROR_HOST=$(MIRROR_HOST) PKG="$(PKG)" docker compose run --rm centos-vault

test-centos-stream:
	docker compose build centos-stream
	MIRROR_HOST=$(MIRROR_HOST) PKG="$(PKG)" docker compose run --rm centos-stream

test-rocky:
	docker compose build rocky
	MIRROR_HOST=$(MIRROR_HOST) docker compose run --rm rocky

test-gentoo:
	docker compose build gentoo
	MIRROR_HOST=$(MIRROR_HOST) docker compose run --rm gentoo

test-qt:
	docker compose build qt
	MIRROR_HOST=$(MIRROR_HOST) docker compose run --rm qt

clean:
	docker compose down --rmi local --remove-orphans 2>/dev/null || docker compose down --remove-orphans

test-msys2:
	docker compose build msys2
	MIRROR_HOST=$(MIRROR_HOST) PKG="$(PKG)" docker compose run --rm msys2

test-deepin:
	docker compose build deepin
	MIRROR_HOST=$(MIRROR_HOST) PKG="$(PKG)" docker compose run --rm deepin

test-deepin-cd:
	docker compose build deepin-cd
	MIRROR_HOST=$(MIRROR_HOST) docker compose run --rm deepin-cd

test-elrepo:
	docker compose build elrepo
	MIRROR_HOST=$(MIRROR_HOST) docker compose run --rm elrepo

test-bioconductor:
	docker compose build bioconductor
	MIRROR_HOST=$(MIRROR_HOST) docker compose run --rm bioconductor

test-docker-ce:
	docker compose build docker-ce
	MIRROR_HOST=$(MIRROR_HOST) docker compose run --rm docker-ce

test-kubernetes:
	docker compose build kubernetes
	MIRROR_HOST=$(MIRROR_HOST) docker compose run --rm kubernetes

test-kali:
	docker compose build kali
	MIRROR_HOST=$(MIRROR_HOST) PKG="$(PKG)" docker compose run --rm kali

test-ros2:
	docker compose build ros2
	MIRROR_HOST=$(MIRROR_HOST) docker compose run --rm ros2

test-rustup:
	docker compose build rustup
	MIRROR_HOST=$(MIRROR_HOST) docker compose run --rm rustup

test-manjaro:
	docker compose build manjaro
	MIRROR_HOST=$(MIRROR_HOST) PKG="$(PKG)" docker compose run --rm manjaro

test-gnu:
	docker compose build gnu
	MIRROR_HOST=$(MIRROR_HOST) docker compose run --rm gnu

test-llvm-apt:
	docker compose build llvm-apt
	MIRROR_HOST=$(MIRROR_HOST) docker compose run --rm llvm-apt

test-mozilla:
	docker compose build mozilla
	MIRROR_HOST=$(MIRROR_HOST) docker compose run --rm mozilla

test-linuxmint:
	docker compose build linuxmint
	MIRROR_HOST=$(MIRROR_HOST) docker compose run --rm linuxmint

test-proxmox:
	docker compose build proxmox
	MIRROR_HOST=$(MIRROR_HOST) docker compose run --rm proxmox

test-kali-images:
	docker compose build kali-images
	MIRROR_HOST=$(MIRROR_HOST) docker compose run --rm kali-images

test-immortalwrt:
	docker compose build immortalwrt
	MIRROR_HOST=$(MIRROR_HOST) docker compose run --rm immortalwrt

test-packman:
	docker compose build packman
	MIRROR_HOST=$(MIRROR_HOST) docker compose run --rm packman

test-raspberrypi:
	docker compose build raspberrypi
	MIRROR_HOST=$(MIRROR_HOST) docker compose run --rm raspberrypi

test-raspbian:
	docker compose build raspbian
	MIRROR_HOST=$(MIRROR_HOST) docker compose run --rm raspbian

test-ros:
	docker compose build ros
	MIRROR_HOST=$(MIRROR_HOST) docker compose run --rm ros

test-termux:
	docker compose build termux
	MIRROR_HOST=$(MIRROR_HOST) docker compose run --rm termux
