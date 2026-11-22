from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'project_alpha_ros'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Akhil',
    maintainer_email='akhil@projectalpha.local',
    description='ROS 2 Jazzy cognitive and motion wrapper package for Project Alpha (Wall-E companion rover)',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'alpha_motion_node = project_alpha_ros.alpha_motion_node:main',
            'alpha_brain_node = project_alpha_ros.alpha_brain_node:main',
            'alpha_face_voice_node = project_alpha_ros.alpha_face_voice_node:main',
        ],
    },
)
