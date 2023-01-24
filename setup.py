from pathlib import Path

from setuptools import find_packages, setup

with open(Path(__file__).resolve().parent / "README.md") as f:
    readme = f.read()

setup(
    name="jeiss-convert",
    url="https://github.com/clbarnes/jeiss-convert",
    author="Chris L. Barnes",
    description="Convert Jeiss .dat files",
    long_description=readme,
    long_description_content_type="text/markdown",
    packages=find_packages(include=["jeiss_convert"]),
    install_requires=[
        "numpy",
        "h5py",
        "tomli; python_version < '3.11'",
        "backports.strenum; python_version < '3.11'",
        "pandas",
        "datetime-matcher",
    ],
    python_requires=">=3.9, <4.0",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    use_scm_version=True,
    setup_requires=["setuptools_scm"],
    entry_points={
        "console_scripts": [
            "dat2hdf5=jeiss_convert.convert:_main",
            "dat2hdf5-verify=jeiss_convert.verify:_main",
            "datmeta=jeiss_convert.meta:_main",
        ]
    },
    package_data={"": ["**/*.tsv", "**/*.toml"]},
)
