import typing as tp
from pathlib import Path

import zarr

from .utils import group_to_bytes, split_channels

StoreFactory = tp.Callable[[Path], zarr.storage.BaseStore]


def _dat_to_zarr(
    store_factory: StoreFactory,
    dat_path: Path,
    container_path: Path,
    group_name: tp.Optional[str] = None,
    ds_kwargs: tp.Optional[dict[str, tp.Any]] = None,
):
    meta, channel_names, data = split_channels(dat_path, True)

    if ds_kwargs is None:
        ds_kwargs = dict()

    if not group_name:
        group_name = "/"

    store = store_factory(container_path)
    container: zarr.Group = zarr.open(store, mode="a")
    if group_name == "/":
        group = container
    else:
        group = container.create_group(group_name)

    group.attrs.update(meta)

    for idx, ds in enumerate(channel_names):
        group.create_dataset(ds, data=data[idx], **ds_kwargs)


def _zarr_to_bytes(
    store_factory: StoreFactory,
    container_path: Path,
    group_name: tp.Optional[str] = None,
):
    if not group_name:
        group_name = "/"

    store = store_factory(container_path)
    container: zarr.Group = zarr.open(store, "r")
    g = container[group_name]
    return group_to_bytes(g, True)


def dat_to_zarr(
    dat_path: Path,
    container_path: Path,
    group_name: tp.Optional[str] = None,
    ds_kwargs: tp.Optional[dict[str, tp.Any]] = None,
):
    return _dat_to_zarr(
        zarr.NestedDirectoryStore, dat_path, container_path, group_name, ds_kwargs
    )


def zarr_to_bytes(container_path: Path, group_name: tp.Optional[str] = None):
    return _zarr_to_bytes(lambda x: x, container_path, group_name)


def dat_to_n5(
    dat_path: Path,
    container_path: Path,
    group_name: tp.Optional[str] = None,
    ds_kwargs: tp.Optional[dict[str, tp.Any]] = None,
):
    return _dat_to_zarr(zarr.N5Store, dat_path, container_path, group_name, ds_kwargs)


def n5_to_bytes(container_path: Path, group_name: tp.Optional[str] = None):
    return _zarr_to_bytes(zarr.N5Store, container_path, group_name)
