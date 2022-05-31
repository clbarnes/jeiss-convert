#!/usr/bin/env python3
"""
Convert a Jeiss FIBSEM .dat file into a standard HDF5,
preserving all known metadata as group attributes,
as well as storing the raw header and footer bytes.
"""
import sys
from argparse import ArgumentParser
from pathlib import Path

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
    parser = ArgumentParser("dat2hdf", description=__doc__)
    parser.add_argument("dat", type=Path, help="Path to a .dat file")
    parser.add_argument("hdf5", type=Path, help="Path to HDF5 file; may exist")
    parser.add_argument(
        "group", nargs="?", help="HDF5 group within the given file; must not exist"
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
    # leave -b for bitshuffle
    parser.add_argument(
        "-B",
        "--byte-shuffle",
        action="store_true",
        help=(
            "Apply the byte shuffle filter, "
            "which may decrease size of compressed data."
        ),
    )
    parser.add_argument(
        "-o",
        "--scale-offset",
        action="store_true",
        help=(
            "Apply the scale-offset filter, which may decrease size of chunked data."
        ),
    )
    parser.add_argument(
        "-f",
        "--fletcher32",
        action="store_true",
        help="Checksum each chunk to allow detection of corruption",
    )

    parsed = parser.parse_args(args)

    ds_kwargs = {}
    if parsed.chunks is not None:
        ds_kwargs["chunks"] = parsed.chunks
    if parsed.compression is not None:
        ds_kwargs.update(parsed.compression)
    if parsed.scale_offset:
        ds_kwargs["scaleoffset"] = 0
    if parsed.byte_shuffle:
        ds_kwargs["shuffle"] = True
    if parsed.fletcher32:
        ds_kwargs["fletcher32"]

    dat_to_hdf5(parsed.dat, parsed.hdf5, parsed.group, ds_kwargs=ds_kwargs)
    return 0


def _main(args=None):
    sys.exit(main(args))


if __name__ == "__main__":
    _main()
