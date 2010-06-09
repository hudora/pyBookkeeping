#!/usr/bin/env python
# encoding: utf-8
"""
pyBookkeeping - Functionality related to bookkeeping
"""

from setuptools import setup, find_packages

setup(name='pyBookkeeping',
      # maintainer='XXX',
      # maintainer_email='xXXXx@hudora.de',
      version='0.1',
      description='Buchhaltungsfunktionen',
      long_description=codecs.open('README.rst', "r", "utf-8").read(),
      classifiers=['License :: OSI Approved :: BSD License',
                   'Intended Audience :: Developers',
                   'Programming Language :: Python'],
      download_url='https://cybernetics.hudora.biz/nonpublic/eggs/',
      packages=find_packages(),
      install_requires=['oauth2', 'cs>=0.11', 'tlslite', 'huSoftM'],
)
