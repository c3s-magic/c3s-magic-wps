#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

import os

from setuptools import setup, find_packages

version = __import__('copernicus').__version__
here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()
CHANGES = open(os.path.join(here, 'CHANGES.rst')).read()

reqs = [line.strip() for line in open('requirements.txt')]

classifiers = [
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Developers',
    'Intended Audience :: Science/Research',
    'Operating System :: MacOS :: MacOS X',
    'Operating System :: POSIX',
    'Programming Language :: Python',
    'Natural Language :: English',
    "Programming Language :: Python :: 2",
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.6',
    'Topic :: Scientific/Engineering :: Atmospheric Science',
    'License :: OSI Approved :: Apache Software License',
]

setup(name='copernicus',
      version=version,
      description="Demo with WPS processes for copernicus.",
      long_description=README + '\n\n' + CHANGES,
      author="Carsten Ehbrecht",
      author_email='ehbrecht@dkrz.de',
      url='https://github.com/cp4cds/copernicus',
      classifiers=classifiers,
      license="Apache Software License 2.0",
      keywords='wps pywps birdhouse copernicus',
      packages=find_packages(),
      include_package_data=True,
      install_requires=reqs,
      entry_points={
          'console_scripts': [
             'copernicus=copernicus.cli:cli',
          ]},)
