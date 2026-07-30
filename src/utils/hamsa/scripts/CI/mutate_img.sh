#!/bin/bash
mkdir -p /home/codething/imagine
mkdir -p /home/codething/imagine/mnt
cd /home/codething/imagine
[ -e jetson-nano-sd-card-image ] || wget https://developer.nvidia.com/jetson-nano-sd-card-image
[ -e sd-blob-b01.img ] || unzip jetson-nano-sd-card-image
l_dev=$(losetup -P -f --show sd-blob-b01.img)
echo $l_dev
mount ${l_dev}p1 mnt
mount --bind /run/resolvconf/resolv.conf mnt/run/resolvconf/resolv.conf
mount --bind /dev mnt/dev
mount --bind /proc mnt/proc
touch mnt/root/install.sh
mount --bind /home/codething/imagine/install.sh mnt/root/install.sh
if [[ `wc -c sd-blob-b01.img` < 19000000000 ]]
then
	truncate -s +5G sd-blob-b01.img
	sgdisk /dev/loop1 -e
	parted /dev/loop1 resizepart 1 20GB
fi
#chroot /home/codething/imagine/mnt
#cd /root
#mkdir build
#cd build
#apt-get install \
#	python3-pip \
#	libopenblas-base \
#	libopenmpi-dev \
#	libjpeg-dev \
#	zlib1g-dev \
#	libpython3-dev \
#	libavcodec-dev \
#	libavformat-dev \
#	libswscale-dev \
#	python3-matplotlib \
#	libffi-dev \
#	gfortran \
#	libopenblas-dev \
#	liblapack-dev
