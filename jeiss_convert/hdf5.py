from pathlib import Path

import h5py

from .utils import group_to_bytes, split_channels


def dat_to_hdf5(
    dat_path: Path,
    hdf5_path: Path,
    hdf5_group=None,
    ds_kwargs=None,
):
    meta, channel_names, data = split_channels(dat_path)

    if ds_kwargs is None:
        ds_kwargs = dict()

    if not hdf5_group:
        hdf5_group = "/"

    with h5py.File(hdf5_path, "a") as h5:
        if hdf5_group == "/":
            g = h5
        else:
            g = h5.create_group(hdf5_group)

        g.attrs.update(meta)

        for idx, ds in enumerate(channel_names):
            g.create_dataset(ds, data=data[idx], **ds_kwargs)


def hdf5_to_bytes(hdf5_path, hdf5_group=None):
    if hdf5_group is None:
        hdf5_group = "/"

    with h5py.File(hdf5_path) as h5:
        g = h5[hdf5_group]
        b = group_to_bytes(g)
    return b
    #     header = write_header(g.attrs)
    #     to_stack = []
    #     for input_id in range(1, 5):
    #         ds_name = f"AI{input_id}"
    #         if ds_name not in g:
    #             continue
    #         to_stack.append(g[ds_name][:])
    #     footer = g.attrs.get("_footer", np.array([], "uint8"))

    # stacked = np.stack(to_stack, axis=0)
    # dtype = stacked.dtype.newbyteorder(DEFAULT_BYTE_ORDER)
    # b = np.asarray(stacked, dtype, order="F").tobytes(order="F")
    # footer_bytes = footer.tobytes()
    # return header + b + footer_bytes
