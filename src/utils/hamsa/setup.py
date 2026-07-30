from glob import glob
from setuptools import setup
from pybind11.setup_helpers import Pybind11Extension

ext_modules = [
    Pybind11Extension(
        "firmware",
        sorted(glob("src/cpp/*.cpp"))+['src/binding/binder.cpp'],  # Sort source files for reproducibility
        include_dirs=["src/cpp/"]
    ),
]

setup(name='hamsa',
      version='1.0',
      description='Software for controlling the Robot Nano Hand',
      author='Kiran Ostrolenk',
      author_email='kiran.ostrolenk@codethink.co.uk',
      url='https://gitlab.com/robot-nano-hand/hamsa',
      packages=['hamsa'],
      package_dir={'hamsa':'src/hamsa'},
      package_data={'hamsa': ['hamsa.config']},
      include_package_data=True,
      ext_package='hamsa',
      ext_modules=ext_modules
     )

