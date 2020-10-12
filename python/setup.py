import platform

from setuptools import find_packages, setup

cmdclass_dict = {}  # type:ignore

# MANIFEST.in ensures that readme and version included into sdist

install_requires = []

dev_requires = [
    "hs-build-tools",
    "pytest",
    "black",
    "isort",
    "pytest",
    "pytest-mypy",
    "pytest-cov",
]


def read_file(f):
    with open(f, "r") as fh:
        return fh.read()


long_description = read_file("README.md")

try:
    from hs_build_tools.release import get_version_and_add_release_cmd

    version = get_version_and_add_release_cmd("version.txt", cmdclass_dict)
except ModuleNotFoundError:
    version = read_file("version.txt").strip()

setup(
    name="base_n",
    version=str(version),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: System :: Archiving :: Backup",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    description="Implementation of varies encoding with configurable base and alphabet",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/hashstore/base_n",
    author="Walnut Geek",
    author_email="wg@walnutgeek.com",
    license="Apache 2.0",
    packages=find_packages(exclude=("*.tests",)),
    package_data={"files": ["mime_infos.json"]},
    cmdclass=cmdclass_dict,
    install_requires=install_requires,
    extras_require={"dev": dev_requires},
    zip_safe=False,
)
