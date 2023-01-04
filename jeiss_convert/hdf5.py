import typing as tp
from pathlib import Path

import h5py
import numpy as np

from .utils import ParsedData, group_to_bytes
from .version import version


def dat_to_hdf5(
    dat_path: Path,
    container_path: Path,
    group_name: tp.Optional[str] = None,
    ds_kwargs: tp.Optional[dict[str, tp.Any]] = None,
):
    if ds_kwargs is None:
        ds_kwargs = dict()

    if not group_name:
        group_name = "/"

    parsed = ParsedData.from_file(dat_path)
    channel_names = parsed.channel_names()

    # meta, channel_names, data = split_channels(dat_path)
    # header_compound = meta_to_compound(meta)

    with h5py.File(container_path, "a") as h5:
        if group_name == "/":
            g = h5
        else:
            g = h5.require_group(group_name)

        g.attrs["dat2hdf5_version"] = version
        # g.attrs.update(meta)
        parsed.header.to_hdf5(g, "_header")

        for idx, ds in enumerate(channel_names):
            g.create_dataset(ds, data=parsed.data[idx], **ds_kwargs)

        if parsed.footer is not None:
            g.create_dataset("_footer", data=np.frombuffer(parsed.footer, "u1"))


def hdf5_to_bytes(hdf5_path, hdf5_group=None):
    if not hdf5_group:
        hdf5_group = "/"

    with h5py.File(hdf5_path) as h5:
        g = h5[hdf5_group]
        b = group_to_bytes(g)
    return b
