#!/usr/bin/env python3
"""
Verify that the contents of an HDF5 container are identical
to an existing Jeiss FIBSEM .dat file,
so that the .dat can be safely deleted.
"""
from contextlib import contextmanager
import sys
from argparse import ArgumentParser
from pathlib import Path

from .hdf5 import hdf5_to_bytes
from .version import version
from .utils import hashsum


def warn(*args, **kwargs):
    kwargs.setdefault("file", sys.stderr)
    print(*args, **kwargs)


def write_dat(fpath: Path, dat_bytes: bytes):
    if fpath.exists():
        warn("Exiting due to existing file at " + str(fpath))
        return 2

    warn(
        "HDF5 files are self-documenting and widely supported. "
        "Dat files are not. "
        "Converting from dat to HDF5 is recommended. "
        "Converting from HDF5 to dat is not."
    )
    response = input(
        "Are you sure you want to create a new dat file? yes/[no] "
    ).strip()
    if response != "yes":
        if response.lower() in ["", "n", "no"]:
            warn("Not writing or validating anything")
            return 0
        warn("Interpreting non-'yes' response " f"'{response}' as negative, exiting")
        return 2

    if str(fpath) == "-":
        sys.stdout.buffer.write(dat_bytes)
    else:
        fpath.write_bytes(dat_bytes)

    return 0


@contextmanager
def open_bytes(fpath: Path):
    if str(fpath) == "-":
        yield sys.stdin.buffer
    else:
        with open(fpath, "rb") as f:
            yield f


def main(args=None):
    parser = ArgumentParser("dat2hdf5-verify", description=__doc__)
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
    parser.add_argument(
        "--write-dat",
        action="store_true",
        help=(
            "Instead of checking the HDF5 for its identity "
            "with an existing dat, write out the calculated dat. "
            "Comes with an interactive warning. Don't do this."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=version,
    )
    parsed = parser.parse_args(args)
    reconverted_bytes = hdf5_to_bytes(parsed.hdf5, parsed.group)

    if parsed.write_dat:
        return write_dat(parsed.dat, reconverted_bytes)

    with open_bytes(parsed.dat) as f:
        dat_sum = hashsum(f)

    reconverted_sum = hashsum(reconverted_bytes)

    if dat_sum != reconverted_sum:
        return 1

    if parsed.delete_dat:
        parsed.dat.unlink()
    return 0


def _main(args=None):
    sys.exit(main(args))


if __name__ == "__main__":
    _main()
