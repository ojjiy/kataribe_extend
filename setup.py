#!/usr/bin/env python

from setuptools import setup, find_packages


def _requires_from_file(filename):
    return open(filename).read().splitlines()


setup(name='line_profiler_extension',
      version='1.0',
      install_requires=_requires_from_file('requirements.txt'),
      url='https://github.com/ojjiy/line_profiler_extension',
      packages=find_packages(include=('reshape.py',)),
      scripts=['reshape.py'])
