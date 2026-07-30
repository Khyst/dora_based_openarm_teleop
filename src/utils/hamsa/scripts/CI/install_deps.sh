# Use `resize2fs` to actualise the partition resizing done as part of the yaml 
resize2fs /dev/loop1p1
# Get `apt-get` ready for the work it's about to do
apt-get update
cd /root
mkdir -p build
cd build
# General packages
apt-get install -y \
		libopenblas-base \
		libopenmpi-dev \
		libjpeg-dev \
		libzmq3-dev \
		zlib1g-dev \
		libpython3-dev \
		libavcodec-dev \
		libavformat-dev \
		libswscale-dev \
		libffi-dev \
		gfortran \
		libopenblas-dev \
		liblapack-dev \
		feh
# Python packages
apt-get install -y python3-pip python3-numpy python3-tqdm python3-traitlets python3-ipywidgets cython3
apt-get install -y python3-matplotlib
pip3 install pycocotools scikit-learn==0.23.2 pybind11 notebook
# Jetson flavoured torch and torchvision
if ! `python3 -c 'import torch' 2> /dev/null`
then 
	wget -q https://nvidia.box.com/shared/static/p57jwntv436lfrd78inwl7iml6p13fzh.whl -O torch-1.8.0-cp36-cp36m-linux_aarch64.whl
	pip3 install torch-1.8.0-cp36-cp36m-linux_aarch64.whl
	rm torch-1.8.0-cp36-cp36m-linux_aarch64.whl
fi
if ! `python3 -c 'import torchvision' 2> /dev/null`
then
	[ -e torchvision ] && rm -rf torchvision
	git clone --branch v0.9.0 https://github.com/pytorch/vision torchvision
	cd torchvision
	export BUILD_VERSION=0.9.0
	python3 setup.py install
	cd ../
fi
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/lib/aarch64-linux-gnu/tegra/
if ! `python3 -c 'import torch2trt' 2> /dev/null`
then
	echo hello
	[ -e torch2trt ] && rm -rf torch2trt
	git clone https://github.com/NVIDIA-AI-IOT/torch2trt
	cd torch2trt
	sudo python3 setup.py install --plugins
	# sudo python3 setup.py install
	cd ../
fi
if ! `python3 -c 'import trt_pose' 2> /dev/null`
then
	[ -e trt_pose ] && rm -rf trt_pose
	git clone https://github.com/NVIDIA-AI-IOT/trt_pose
	cd trt_pose
	python3 setup.py install
	cd ../	
fi
if ! `python3 -c 'import jetcam' 2> /dev/null`
then
	[ -e jetcam ] && rm -rf jetcam
	git clone https://github.com/NVIDIA-AI-IOT/jetcam
	cd jetcam
	sed -i 's/nvvidconv ! video/nvvidconv flip-method=2 ! video/' jetcam/csi_camera.py
	python3 setup.py install
	cd ../
fi
if [ ! -e /usr/sbin/useradd.default ]
then
	mv /usr/sbin/useradd /usr/sbin/useradd.default
	echo -e '#!/bin/bash\nuseradd.default -G dialout "$@"' > /usr/sbin/useradd
	chmod +x /usr/sbin/useradd
fi

sed -i 's,${totalmem}" / 2,${totalmem}" * 3 / 2,' /etc/systemd/nvzramconfig.sh

mkdir -p /etc/skel/robothand
[ -e /etc/skel/robothand/trt_pose_hand ] && rm -rf /etc/skel/robothand/trt_pose_hand
git clone https://github.com/NVIDIA-AI-IOT/trt_pose_hand /etc/skel/robothand/trt_pose_hand
# [ -e /etc/skel/robothand/hamsa ] && rm -rf /etc/skel/robothand/hamsa
# git clone https://gitlab.com/robot-nano-hand/hamsa /etc/skel/robothand/hamsa
