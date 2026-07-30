from setuptools import find_packages, setup

package_name = 'hamsa_motion'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/hamsa.launch.py']),
        ('share/' + package_name + '/config', ['config/hamsa_params.yaml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='khy',
    maintainer_email='yonghun@rastech.co.kr',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'hamsa_motion_node = hamsa_motion.hamsa_motion_node:main'
        ],
    },
)
