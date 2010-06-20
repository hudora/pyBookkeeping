#!/usr/bin/env python
# encoding: utf-8

"""pyBookkeeping implements misc functionality to access bookkeeping systems,
most prominentely xero.com.
"""

from setuptools import setup, find_packages
import codecs

setup(name='pyBookkeeping',
      maintainer='Maximillian Dornseif',
      maintainer_email='md@hudora.de',
      version='1.0p1',
      description='Buchhaltungsfunktionen',
      long_description=codecs.open('README.rst', "r", "utf-8").read(),
      classifiers=['License :: OSI Approved :: BSD License',
                   'Intended Audience :: Developers',
                   'Programming Language :: Python'],
      packages=find_packages(),
      include_package_data=True,
      install_requires=['oauth2', 'cs>=0.11', 'tlslite', 'huSoftM'],
)
