import typing as tp
from pathlib import Path

import h5py

from .utils import group_to_bytes, split_channels


def dat_to_hdf5(
    dat_path: Path,
    container_path: Path,
    group_name: tp.Optional[str] = None,
    ds_kwargs: tp.Optional[dict[str, tp.Any]] = None,
):
    meta, channel_names, data = split_channels(dat_path)

    if ds_kwargs is None:
        ds_kwargs = dict()

    if not group_name:
        group_name = "/"

    with h5py.File(container_path, "a") as h5:
        if group_name == "/":
            g = h5
        else:
            g = h5.create_group(group_name)

        g.attrs.update(meta)

        for idx, ds in enumerate(channel_names):
            g.create_dataset(ds, data=data[idx], **ds_kwargs)


def hdf5_to_bytes(hdf5_path, hdf5_group=None):
    if not hdf5_group:
        hdf5_group = "/"

    with h5py.File(hdf5_path) as h5:
        g = h5[hdf5_group]
        b = group_to_bytes(g)
    return b
