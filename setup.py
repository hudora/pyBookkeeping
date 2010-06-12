#!/usr/bin/env python
# encoding: utf-8
"""pyBookkeeping implements misc functionality to access bookkeeping systems,
most prominentely xero.com.
"""

# setup.py
# Created by Maximillian Dornseif on 2010-04-07 for HUDORA.
# Copyright (c) 2010 HUDORA. All rights reserved.

from setuptools import setup, find_packages

setup(name='pyBookkeeping',
      maintainer='Maximillian Dornseif',
      maintainer_email='md@hudora.de',
      version='1.0',
      description='xXXXx FILL IN HERE xXXXx',
      long_description=long_description=codecs.open('README.rst', "r", "utf-8").read(),
      classifiers=['License :: OSI Approved :: BSD License',
                   'Intended Audience :: Developers',
                   'Programming Language :: Python'],
      packages=find_packages(),
      include_package_data=True,
      install_requires=['oauth2', 'tlslite'],
)
