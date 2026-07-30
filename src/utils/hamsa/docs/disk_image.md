# Disk image

In order to reproduce the SD card image you will first need to flash a card with a JetPack image. Then install the following packages:

* [`trt_pose_hand`](https://github.com/NVIDIA-AI-IOT/trt_pose_hand)
* [`trt_pose`](https://github.com/NVIDIA-AI-IOT/trt_pose)
* [`jetcam`](https://github.com/NVIDIA-AI-IOT/jetcam)

Follow the recommended steps detailed in the README's of these packages. If you wish to use the notebook then you will of course also need Jupyter.

Next install `hamsa`. Run the following commands in the same directory containing the `trt_pose_hand` directory:

```bash
pip3 install pybind11 --user
git clone https://gitlab.com/CodethinkLabs/hamsa.git
cd hamsa
make
```

The first command may not be necessary as you probably already installed pybind11 as part of the previous dependencies.

You will also need to install add the user to the group `dialout`. This gives write access to `/dev/ttyUSB0`. Run:

```bash
sudo gpasswd --add $USER dialout
```

Finally, you will need to invert the camera feed. Find the `jetcam` egg by running:

```bash
python3 -c "import jetcam; print(jetcam.__file__)"
```

Unzip it and then modify the `jetcam/csi_camera.py` file:

```bash
sed -i 's/nvvidconv ! video/nvvidconv flip-method=2 ! video/' jetcam/csi_camera.py
```

Now recreate the egg file and replace the original.


To stop hitting memory limits we increased the swap size in 
`/etc/systemd/nvramconfig.sh`

editing this line
```python
mem=$((("${totalmem}" / 2 / "${NRDEVICES}") * 1024))
``` 
to 
```python
mem=$((("${totalmem}" * 3 / 2 / "${NRDEVICES}") * 1024))
```
