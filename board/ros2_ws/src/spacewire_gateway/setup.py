import os
from glob import glob

from setuptools import find_packages, setup

package_name = 'spacewire_gateway'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        (
            'share/ament_index/resource_index/packages',
            ['resource/' + package_name],
        ),
        ('share/' + package_name, ['package.xml']),
        (
            os.path.join('share', package_name, 'launch'),
            glob('launch/*launch.py'),
        ),
    ],
    package_data={
        'spacewire_gateway.hardware.lowlevel': ['libmmio32.so'],
    },
    install_requires=['setuptools'],
    zip_safe=False,
    maintainer='arthur-24',
    maintainer_email='arthur-24@todo.todo',
    description='ROS 2 gateway for the BeagleV-Fire SpaceWire interface',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'gateway = spacewire_gateway.gateway:main',
        ],
    },
)
