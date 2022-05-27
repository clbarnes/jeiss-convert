#!/usr/bin/env python3
from argparse import ArgumentParser
from pathlib import Path
import sys

from .utils import dat_to_hdf5


def parse_chunks(s: str):
    if s == "auto":
        return True
    return tuple(int(i.strip()) for i in s.split(","))


def parse_compression(s: str):
    if s == "lzf":
        return {"compression": "lzf"}

    if s.startswith("gzip"):
        c = {"compression": "gzip"}
        if len(s) > 4:
            c["compression_opts"] = int(s[4:])
        return c

    raise ValueError(f"Unknown compression type '{s}'")


def main(args=None):
    parser = ArgumentParser("dat2hdf")
    parser.add_argument("dat", type=Path, help="Path to a .dat file")
    parser.add_argument("hdf5", type=Path, help="Path to HDF5 file; may exist")
    parser.add_argument(
        "group", nargs="?", help="HDF5 group within the given file; must not exist"
    )
    parser.add_argument(
        "-a",
        "--analog-input",
        action="append",
        type=int,
        choices=[1, 2, 3, 4],
        help="Which analog inputs to include (default all available)",
    )
    parser.add_argument(
        "-c",
        "--chunks",
        type=parse_chunks,
        help=(
            "Chunking scheme (default none) "
            "as comma-separated integers in XY, "
            "or 'auto' for automatic."
        ),
    )
    parser.add_argument(
        "-z",
        "--compression",
        type=parse_compression,
        help=(
            "Compression to use (default none); "
            "should be 'lzf' or 'gzip'. "
            "Gzip can be suffixed with the level 0-9."
        ),
    )

    parsed = parser.parse_args(args)

    ds_kwargs = {}
    if parsed.chunks is not None:
        ds_kwargs["chunks"] = parsed.chunks
    if parsed.compression is not None:
        ds_kwargs.update(parsed.compression)

    dat_to_hdf5(
        parsed.dat, parsed.hdf5, parsed.group, parsed.analog_input, ds_kwargs=ds_kwargs
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
