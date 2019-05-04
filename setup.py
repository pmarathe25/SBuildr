#!/usr/bin/env python
from setuptools import setup, find_packages
import os
import srbuild

curdir = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(curdir, "README.md")) as f:
    long_description = f.read()

setup(
    name="SRBuild",
    version=srbuild.__version__,
    description="A python-based meta-build system for C++ projects.",
    long_description=long_description,
    author="Pranav Marathe",
    author_email="pmarathe25@gmail.com",
    python_requires=">=3",
    url="https://github.com/pmarathe25/SRBuild",
    zip_safe=True,
    packages=find_packages(),
    license="GNU GPLv3",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
    ],
)
