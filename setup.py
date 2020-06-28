#!/usr/bin/python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(name='stream-sim-backend',
      version='0.1.0',
      description='Simple streaming simulator - the backend',
      url='https://github.com/robotics-4-all/stream-sim-backend',
      author='Manos Tsardoulias',
      author_email='etsardou@ece.auth.gr',
      license='Apache v2',
      packages=find_packages(),
      install_requires= [],
      test_suite='nose.collector',
      tests_require=['nose'],
      zip_safe=False
)
