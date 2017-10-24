##
# \file setup.py
#
# Instructions:
# 1) Set environment variables with prefix NIFTYMIC_, e.g.
#   `export NIFTYMIC_ITK_DIR=path-to-ITK_NIFTYMIC-build`
#   to incorporate `-D ITK_DIR=path-to-ITK_NIFTYMIC-build` in `cmake` build.
# 2) `pip install -e .`
#   All python packages and command line tools are then installed during
#
# \author     Michael Ebner (michael.ebner.14@ucl.ac.uk)
# \date       July 2017
#


import re
import os
import sys
from setuptools import setup
from setuptools.command.develop import develop
from setuptools.command.install import install

from install_cli import main as install_cli


##
# Post-installation to build additionally required command line interface tools
# located in niftymic/cli.
# \date       2017-10-20 17:00:53+0100
#
class PostDevelopCommand(develop):

    def run(self):
        install_cli()
        develop.run(self)


##
# Post-installation to build additionally required command line interface tools
# located in niftymic/cli.
# \date       2017-10-20 17:00:53+0100
#
class PostInstallCommand(install):

    def run(self):
        install_cli()
        install.run(self)


description = "Motion Correction and Volumetric Image Reconstruction of 2D " \
    "Ultra-fast MRI"
long_description = "This is a research-focused toolkit developed within the" \
    " [GIFT-Surg](http: // www.gift-surg.ac.uk/) project to reconstruct an " \
    "isotropic, high-resolution volume from multiple, possibly " \
    "motion-corrupted, stacks of low-resolution 2D slices. The framework " \
    "relies on slice-to-volume registration algorithms for motion " \
    "correction and reconstruction-based Super-Resolution(SR) techniques " \
    "for the volumetric reconstruction." \
    "The entire reconstruction pipeline is programmed in Python by using a " \
    "mix of SimpleITK, WrapITK and standard C++ITK."


setup(name='NiftyMIC',
      version='0.1.dev1',
      description=description,
      long_description=long_description,
      url='https://github.com/gift-surg/NiftyMIC',
      author='Michael Ebner',
      author_email='michael.ebner.14@ucl.ac.uk',
      license='BSD-3-Clause',
      packages=['niftymic'],
      install_requires=[
          'pysitk',
          'nsol',
          'simplereg',
          'scikit_image>=0.12.3',
          'scipy>=0.19.1',
          'natsort>=5.0.3',
          'numpy>=1.13.1',
          'SimpleITK>=1.0.1',
      ],
      zip_safe=False,
      keywords='development numericalsolver convexoptimisation',
      classifiers=[
          'Development Status :: 3 - Alpha',

          'Intended Audience :: Developers',
          'Topic :: Software Development :: Build Tools',

          'License :: OSI Approved :: BSD License',

          'Programming Language :: Python',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 2.7',
      ],
      cmdclass={
          'develop': PostDevelopCommand,
          "install": PostInstallCommand,
      },
      entry_points={
          'console_scripts': [
              'niftymic_correct_bias_field = niftymic.application.correct_bias_field:main',
              'niftymic_reconstruct_volume = niftymic.application.reconstruct_volume:main',
              'niftymic_reconstruct_volume_from_slices = niftymic.application.reconstruct_volume_from_slices:main',
              'niftymic_register_to_template = niftymic.application.register_to_template:main',
              'niftymic_run_intensity_correction = niftymic.application.run_intensity_correction:main',
              'niftymic_run_reconstruction_parameter_study = niftymic.application.run_reconstruction_parameter_study:main',
              'niftymic_show_reconstruction_parameter_study = nsol.application.show_parameter_study:main',
          ],
      },
      )
