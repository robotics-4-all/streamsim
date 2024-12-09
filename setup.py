#!/usr/bin/python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(name='streamsim',
      version='0.1.0',
      description='Simple streaming simulator',
      url='https://github.com/robotics-4-all/streamsim',
      author='Manos Tsardoulias',
      author_email='etsardou@ece.auth.gr',
      license='Apache v2',
      packages=find_packages(),
      install_requires= [],
      test_suite='nose.collector',
      tests_require=['nose'],
      zip_safe=False
)
