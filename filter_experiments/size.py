#!/usr/bin/env python3
import csv
import itertools
import logging
import time
import typing as tp
from io import BytesIO

import h5py
import hdf5plugin as h5p
import pooch
from tqdm import tqdm

from jeiss_convert.utils import ParsedData

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

logger.info("Retrieving data")
dat_path = pooch.retrieve(
    "https://neurophyla.mrc-lmb.cam.ac.uk/share/fibsem_example/FIBdeSEMAna_21-12-26_005024_0-0-0.dat",
    None,
)
logger.info("Reading file")

parsed = ParsedData.from_file(dat_path)
c0 = parsed.data[0:1]

shuffle = [False, True]
scale_offset = [None, 0]
compression = [None, "gzip", "lzf"]


def profile_dataset(array, **kwargs):
    b = BytesIO()
    f = h5py.File(b, "w")
    name = "data"
    start = time.process_time()
    f.create_dataset(name, data=array, chunks=True, **kwargs)
    write_stop = time.process_time()
    _ = f[name][:]
    read_stop = time.process_time()
    return write_stop - start, read_stop - write_stop, len(b.getvalue()), kwargs


def fmt_num(n):
    return f"{n:.2f}"


logger.info("Getting reference values")
ref_wtime, ref_rtime, ref_size, ref_args = profile_dataset(c0)
to_do: list[tuple[tp.Optional[str], tp.Mapping[str, tp.Any]]] = []
for sh, sc, cmp in itertools.product(shuffle, scale_offset, compression):
    items = []
    if sh:
        items.append("byteshuffle")
    if sc is not None:
        items.append("scaleoffset")
    if cmp:
        items.append(cmp)
    to_do.append(
        ("+".join(items), {"shuffle": sh, "scaleoffset": sc, "compression": cmp})
    )

to_do.extend(
    [
        ("bitshuffle", h5p.Bitshuffle(lz4=False)),
        ("bitshuffle+lz4", h5p.Bitshuffle(lz4=True)),
        ("lz4", h5p.LZ4()),
        ("zstd", h5p.Zstd()),
    ]
)
shuffle_names = ["0sh", "Bsh", "bsh"]
to_do.extend(
    (f"blosc+{cname}+{shuffle_names[sh]}", h5p.Blosc(cname, shuffle=sh))
    for cname, sh in itertools.product(
        ["blosclz", "lz4", "lz4hc", "zlib", "zstd"], [0, 1, 2]
    )
)

with open("benches.tsv", "w") as f:
    writer = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_NONE)
    writer.writerow(
        ["x_wtime", "x_rtime", "x_size", "wtime(s)", "rtime(s)", "size(B)", "kwargs"]
    )
    # writer.writerow(
    #     [
    #         fmt_num(1.0),
    #         fmt_num(1.0),
    #         fmt_num(1.0),
    #         fmt_num(ref_wtime),
    #         fmt_num(ref_rtime),
    #         ref_size,
    #         "",
    #     ]
    # )
    for arg_str, kwargs in tqdm(to_do, "Parameter combinations"):
        logger.debug("Running with %s", arg_str)
        wt, rt, s, _ = profile_dataset(c0, **kwargs)
        writer.writerow(
            [
                fmt_num(wt / ref_wtime),
                fmt_num(rt / ref_rtime),
                fmt_num(s / ref_size),
                fmt_num(wt),
                fmt_num(rt),
                s,
                arg_str,
            ]
        )
