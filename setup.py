#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='loon',
    version='0.1',
    description="RAVEn Smart Meter API.",
    author="Josh Bode",
    author_email='joshbode@gmail.com',
    install_requires=[
        'pyserial',
    ],
    license='LICENSE.txt',
    packages=find_packages(),
    long_description=open('README.txt', 'r').read(),
    #entry_points={
    #    'console_scripts': [
    #        'dextr = nab.dextr:main',
    #    ]
    #},
)
