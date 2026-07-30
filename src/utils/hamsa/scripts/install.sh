set -e
mkdir -p $1
cd $1

# Install torch
wget https://nvidia.box.com/shared/static/p57jwntv436lfrd78inwl7iml6p13fzh.whl -O torch-1.8.0-cp36-cp36m-linux_aarch64.whl
sudo apt-get install python3-pip libopenblas-base libopenmpi-dev 
pip3 install Cython --user
pip3 install numpy torch-1.8.0-cp36-cp36m-linux_aarch64.whl --user
rm torch-1.8.0-cp36-cp36m-linux_aarch64.whl

# torchvision
sudo apt-get install libjpeg-dev zlib1g-dev libpython3-dev libavcodec-dev libavformat-dev libswscale-dev
[ -e torchvision ] && rm -rf torchvision
git clone --branch v0.9.0 https://github.com/pytorch/vision torchvision   # see below for version of torchvision to download
cd torchvision
export BUILD_VERSION=0.9.0
python3 setup.py install --user
cd ../  # attempting to load torchvision from build dir will result in import error
# pip install 'pillow<7' # always needed for Python 2.7, not needed torchvision v0.5.0+ with Python 3.6

# # torch2trt
[ -e torch2trt ] && rm -rf torch2trt
git clone https://github.com/NVIDIA-AI-IOT/torch2trt
cd torch2trt
sudo python3 setup.py install --plugins --user
cd ../

# # Misc
pip3 install tqdm cython pycocotools --user
sudo apt-get install python3-matplotlib  libffi-dev

# # trt_pose
[ -e trt_pose ] && rm -rf trt_pose
git clone https://github.com/NVIDIA-AI-IOT/trt_pose
cd trt_pose
python3 setup.py install --user
cd ../

# Jetcam
pip3 install traitlets --user
[ -e jetcam ] && rm -rf jetcam
git clone https://github.com/NVIDIA-AI-IOT/jetcam
cd jetcam
sudo python3 setup.py install
cd ../

# Jupyter
pip3 install jupyterlab ipywidgets --user

# Invert camera
jetcam_path=$(python3 -c "import jetcam; print('/'.join(jetcam.__file__.split('/')[:-2]))")
jetcam_file=$(basename $jetcam_path)
cp $jetcam_path .
unzip $jetcam_file
sed -i 's/nvvidconv ! video/nvvidconv flip-method=2 ! video/' jetcam/csi_camera.py
zip -r $jetcam_file EGG-INFO jetcam
sudo cp $jetcam_file $jetcam_path

# trt_pose_hand
[ -e trt_pose_hand ] && rm -rf trt_pose_hand
git clone https://github.com/NVIDIA-AI-IOT/trt_pose_hand
sudo apt-get install gfortran libopenblas-dev liblapack-dev
pip3 install scikit-learn==0.23.2