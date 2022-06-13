#!/usr/bin/env python3
"""
Verify that the contents of an HDF5 container are identical
to an existing Jeiss FIBSEM .dat file,
so that the .dat can be safely deleted.
"""
import hashlib
import sys
from argparse import ArgumentParser
from pathlib import Path

from .utils import hdf5_to_bytes
from .version import version


def md5sum(b):
    md5 = hashlib.md5()
    md5.update(b)
    return md5.hexdigest()


def noop(arg):
    return arg


def warn(*args, **kwargs):
    kwargs.setdefault(file=sys.stderr)
    print(*args, **kwargs)


def write_dat(fpath: Path, hdf5_path, group=None):
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
        warn(
            "Interpreting response non-'yes' response "
            f"'{response}' as negative, exiting"
        )
        return 2

    b = hdf5_to_bytes(hdf5_path, group)
    if str(fpath) == "-":
        sys.stdout.buffer.write(b)
    else:
        fpath.write_bytes(b)


def read_bytes(fpath: Path):
    if str(fpath) == "-":
        return sys.stdin.buffer.read()
    return fpath.read_bytes()


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
        "-s",
        "--strict",
        action="store_true",
        help="Check for identity of bytes rather than hash (slow and unnecessary)",
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
    if parsed.write_dat:
        return write_dat(parsed.dat, parsed.hdf5, parsed.group)

    fn = noop if parsed.strict else md5sum

    dat = fn(read_bytes(parsed.dat))
    hdf5 = fn(hdf5_to_bytes(parsed.hdf5, parsed.group))

    if dat != hdf5:
        return 1

    if parsed.delete_dat:
        parsed.dat.unlink()
    return 0


def _main(args=None):
    sys.exit(main(args))


if __name__ == "__main__":
    _main()
