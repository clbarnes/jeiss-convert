#!/usr/bin/env python3
"""
Convert a Jeiss FIBSEM .dat file into a standard HDF5 group
(which may be the container's root),
preserving all known metadata as group attributes.
Additionally stores the raw header and footer bytes as uint8 arrays
(under keys "_header" and "_footer" respectively),
the version string of the conversion tool ("_dat2hdf5_version").

Each channel which exists is stored as a dataset within the group
named "AI1", "AI2", ..., based on the original base-1 channel index
("AI" stands for "Analogue Input").
Channel datasets optionally store the minimum and maximum values
as attributes "min" and "max".
Datasets may optionally be chunked, compressed, and/or have other filters applied.

Lastly, additional metadata from a CSV indexed by acquisition date and time
can be included as attributes on an empty "additional_metadata" subgroup.
"""
import datetime as dt
import logging
import sys
import typing as tp
from argparse import ArgumentParser
from pathlib import Path

import pandas as pd

from .csvmeta import datetime_from_path, get_csv_metadata
from .hdf5 import dat_to_hdf5
from .version import version

logger = logging.getLogger(__name__)


def parse_chunks(s: str):
    if s == "auto":
        return True
    tup = tuple(int(i.strip()) for i in s.split(","))
    if len(tup) == 1:
        tup += tup
    if len(tup) != 2:
        raise ValueError(
            "Chunks must be 'auto', a single integer, or two comma-separated integers"
        )
    return tup


def parse_compression(s: str):
    if s == "lzf":
        return {"compression": "lzf"}

    if s.startswith("gzip"):
        c = {"compression": "gzip"}
        if len(s) > 4:
            c["compression_opts"] = int(s[4:])
        return c

    raise ValueError(f"Unknown compression type '{s}'")


def parse_csv_metadata(
    dat_path: Path,
    csv_path: tp.Optional[Path],
    datetime: tp.Optional[dt.datetime],
    datetime_pattern: tp.Optional[str],
) -> tp.Optional[dict[str, tp.Any]]:
    if datetime and datetime_pattern:
        raise ValueError(
            "Explicit datetime and datetime_pattern given; only one should be given"
        )

    if not csv_path:
        if datetime or datetime_pattern:
            logger.warning(
                "datetime and datetime_pattern given, but no csv_path; ignoring"
            )

        return None

    elif datetime_pattern:

        datetime = datetime_from_path(dat_path, datetime_pattern)

    elif not datetime:
        raise ValueError(
            "CSV path given but no datetime or datetime_pattern, cannot identify entry"
        )

    df = pd.read_csv(csv_path)

    return get_csv_metadata(df, datetime)


def main(args=None):
    parser = ArgumentParser("dat2hdf5", description=__doc__)
    parser.add_argument("dat", type=Path, help="Path to a .dat file")
    parser.add_argument("hdf5", type=Path, help="Path to HDF5 file; may exist")
    parser.add_argument(
        "group", nargs="?", help="HDF5 group within the given file; must not exist"
    )
    parser.add_argument(
        "-m",
        "--minmax",
        action="store_true",
        help="Calculate each array's min and max values and store as attributes",
    )
    parser.add_argument(
        "-c",
        "--chunks",
        type=parse_chunks,
        help=(
            "Chunking scheme (default none) "
            "as a single integer for a square chunk, "
            "comma-separated integers in XY, "
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
    parser.add_argument(
        "--csv-path",
        "-p",
        type=Path,
        help=(
            "Path to metadata CSV. "
            "Must be paired with --datetime (-d) or --datetime-pattern (-D) "
            "so that the file can be matched to an entry."
        ),
    )
    parser.add_argument(
        "--datetime",
        "-d",
        type=dt.datetime.fromisoformat,
        help=(
            "Acquisition datetime in ISO-8601 format; "
            "only used to match file to its entry in a metadata CSV"
        ),
    )
    parser.add_argument(
        "--datetime-pattern",
        "-D",
        help=(
            r"Dfregex (i.e. regex plus C-like date/time codes) "
            "showing how to parse the acquisition date and time from the filename; "
            "only used to match file to its entry in a metadata CSV. "
            "See here for more details: "
            "https://github.com/stephen-zhao/datetime_matcher"
            "#dfregex-syntax-informal-spec"
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=version,
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

    meta = parse_csv_metadata(
        parsed.dat, parsed.csv_path, parsed.datetime, parsed.datetime_pattern
    )

    dat_to_hdf5(
        parsed.dat,
        parsed.hdf5,
        parsed.group,
        ds_kwargs=ds_kwargs,
        minmax=parsed.minmax,
        additional_metadata=meta,
    )
    return 0


def _main(args=None):
    sys.exit(main(args))


if __name__ == "__main__":
    _main()
