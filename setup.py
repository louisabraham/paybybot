#!/usr/bin/env python3

import os
from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="paybybot",
    version="0.0.4",
    author="Louis Abraham",
    license="MIT",
    author_email="louis.abraham@yahoo.fr",
    description="Notifications for https://www.paybyphone.fr/",
    long_description=read("README.rst"),
    url="https://github.com/louisabraham/paybybot",
    packages=["paybybot"],
    install_requires=["selenium", "dateparser", "pyyaml", "schedule"],
    python_requires=">=3.5",
    entry_points={"console_scripts": ["paybybot = paybybot:main"]},
    classifiers=["Topic :: Utilities"],
)
