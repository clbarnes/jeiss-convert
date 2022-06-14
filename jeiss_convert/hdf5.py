from pathlib import Path

import h5py
import numpy as np

from .version import version
from .utils import ParsedData, write_header, DEFAULT_BYTE_ORDER

def dat_to_hdf5(
    dat_path: Path,
    hdf5_path: Path,
    hdf5_group=None,
    ds_kwargs=None,
):
    if ds_kwargs is None:
        ds_kwargs = dict()

    if hdf5_group is None:
        hdf5_group = "/"

    all_data = ParsedData.from_file(dat_path)

    ds_to_channel = dict()
    max_channel = 0
    for input_id in range(1, 5):
        ds = f"AI{input_id}"

        if all_data.meta[ds]:
            ds_to_channel[ds] = max_channel
            max_channel += 1

    with h5py.File(hdf5_path, "a") as h5:
        if hdf5_group == "/":
            g = h5
        else:
            g = h5.create_group(hdf5_group)

        g.attrs.update(all_data.meta)

        if all_data.header is not None:
            g.attrs["_header"] = np.frombuffer(all_data.header, dtype="uint8")
        if all_data.footer is not None:
            g.attrs["_footer"] = np.frombuffer(all_data.footer, dtype="uint8")

        g.attrs["_dat2hdf5_version"] = version
        for ds, channel_idx in ds_to_channel.items():
            g.create_dataset(ds, data=all_data.data[channel_idx], **ds_kwargs)


def hdf5_to_bytes(hdf5_path, hdf5_group=None):
    if hdf5_group is None:
        hdf5_group = "/"

    with h5py.File(hdf5_path) as h5:
        g = h5[hdf5_group]
        header = write_header(g.attrs)
        to_stack = []
        for input_id in range(1, 5):
            ds_name = f"AI{input_id}"
            if ds_name not in g:
                continue
            to_stack.append(g[ds_name][:])
        footer = g.attrs.get("_footer", np.array([], "uint8"))

    stacked = np.stack(to_stack, axis=0)
    dtype = stacked.dtype.newbyteorder(DEFAULT_BYTE_ORDER)
    b = np.asarray(stacked, dtype, order="F").tobytes(order="F")
    footer_bytes = footer.tobytes()
    return header + b + footer_bytes
