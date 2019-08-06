#!/usr/bin/env python
from setuptools import setup, find_packages
import os
import sbuildr

curdir = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(curdir, "README.md")) as f:
    long_description = f.read()

setup(
    name="SBuildr",
    version=sbuildr.__version__,
    description="A python-based meta-build system for C++ projects.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Pranav Marathe",
    author_email="pmarathe25@gmail.com",
    python_requires=">=3",
    url="https://github.com/pmarathe25/SBuildr",
    zip_safe=True,
    packages=find_packages(),
    scripts=["bin/sbuildr"],
    license="GNU GPLv3",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
    ],
)
