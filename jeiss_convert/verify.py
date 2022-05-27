#!/usr/bin/env python3
from argparse import ArgumentParser
from pathlib import Path
import hashlib
import sys

from .utils import hdf5_to_bytes


def md5sum(b):
    md5 = hashlib.md5()
    md5.update(b)
    return md5.hexdigest()


def main(args=None):
    parser = ArgumentParser("dat2hdf-verify")
    parser.add_argument("dat", type=Path, help="Path to a .dat file")
    parser.add_argument("hdf5", type=Path, help="Path to HDF5 file; may exist")
    parser.add_argument(
        "group",
        nargs="?",
        help="HDF5 group within the given file, default root; otherwise must not exist",
    )
    parser.add_argument(
        "-d",
        "--delete-dat",
        action="store_true",
        help="Delete the .dat file if the check succeeds",
    )
    parsed = parser.parse_args(args)

    dat_md5 = md5sum(parsed.dat.read_bytes())
    hdf5_md5 = md5sum(hdf5_to_bytes(parsed.hdf5, parsed.group))
    if dat_md5 != hdf5_md5:
        return 1

    if parsed.delete_dat:
        parsed.dat.unlink()
    return 0


if __name__ == "__main__":
    sys.exit(main())
