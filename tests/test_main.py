from pathlib import Path

import pytest
import h5py
import numpy as np
import zarr

from jeiss_convert import convert, verify
from jeiss_convert.hdf5 import dat_to_hdf5, hdf5_to_bytes
from jeiss_convert.misc import HEADER_LENGTH
from jeiss_convert.utils import md5sum, metadata_to_jso, metadata_to_numpy, split_channels, write_header
from jeiss_convert.zr import dat_to_n5, dat_to_zarr, n5_to_bytes, zarr_to_bytes


def test_importable():
    import jeiss_convert

    assert jeiss_convert.__version__


def test_cli_convert_verify(dat_path, tmpdir):
    hdf5_path = Path(tmpdir / "data.hdf5")
    conv_status = convert.main([str(dat_path), str(hdf5_path)])
    assert conv_status == 0
    assert hdf5_path.is_file()
    verif_status = verify.main([str(dat_path), str(hdf5_path)])
    assert verif_status == 0


def assert_arrays_equal(test: np.ndarray, ref: np.ndarray):
    assert test.dtype == ref.dtype
    assert test.shape == ref.shape
    assert test.ravel()[0] == ref.ravel()[0]
    assert np.allclose(test, ref)


def assert_channel_arrays_equal(test: dict[str, np.ndarray], ref: dict[str, np.ndarray]):
    assert set(test) == set(ref)
    for key, a_val in test.items():
        assert_arrays_equal(a_val, ref[key])


def channel_dict(names, data) -> dict[str, np.ndarray]:
    d = {cn: data[idx] for idx, cn in enumerate(names)}
    return d


def test_array_roundtrip_hdf5(dat_path, tmpdir):
    out_path = Path(tmpdir / "data.hdf5")
    _, channel_names, data = split_channels(dat_path)
    dat_arrays = channel_dict(channel_names, data)

    dat_to_hdf5(dat_path, out_path)

    with h5py.File(out_path) as h5f:
        written_arrays: dict[str, np.ndarray] = {cn: h5f[cn][:] for cn in channel_names}

    for cn in channel_names:
        assert_arrays_equal(dat_arrays[cn], written_arrays[cn])


def test_array_roundtrip_zarr(dat_path, tmpdir):
    out_path = Path(tmpdir / "data.zarr")
    _, channel_names, data = split_channels(dat_path)
    dat_arrays = channel_dict(channel_names, data)

    dat_to_zarr(dat_path, out_path)

    container = zarr.open(out_path, "r")
    written_arrays: dict[str, np.ndarray] = {cn: container[cn][:] for cn in channel_names}

    for cn in channel_names:
        assert_arrays_equal(dat_arrays[cn], written_arrays[cn])


@pytest.mark.skip("dtype byte order mismatch")
def test_array_roundtrip_n5(dat_path, tmpdir):
    out_path = Path(tmpdir / "data.zarr")
    _, channel_names, data = split_channels(dat_path)
    dat_arrays = channel_dict(channel_names, data)

    dat_to_n5(dat_path, out_path)

    container = zarr.open(zarr.N5Store(out_path), "r")
    written_arrays: dict[str, np.ndarray] = {cn: container[cn][:] for cn in channel_names}

    for cn in channel_names:
        assert_arrays_equal(dat_arrays[cn], written_arrays[cn])


# todo: check array bytes
# todo: check footer bytes


def assert_metadata_contains_values(test, ref):
    """test must be superset of ref. test must contain vals coercible into dtypes of ref"""
    for k, ref_v in ref.items():
        if k.startswith("_"):
            continue
        assert k in test
        test_v = test[k]
        assert test_v == ref_v


def read_header_bytes(path):
    with open(path, "rb") as f:
        return f.read(HEADER_LENGTH)


def test_meta_jso_roundtrip_hdf5(dat_path, tmpdir):
    out_path = Path(tmpdir / "data.zarr")
    meta, _, _ = split_channels(dat_path)
    ref_jso = metadata_to_jso(meta)

    dat_to_hdf5(dat_path, out_path)

    with h5py.File(out_path, "r") as container:
        test_jso = metadata_to_jso(container.attrs)
        test_bytes = write_header(container.attrs)

    assert_metadata_contains_values(test_jso, ref_jso)

    ref_bytes = read_header_bytes(dat_path)
    assert test_bytes == ref_bytes


def test_meta_jso_roundtrip_zarr(dat_path, tmpdir):
    out_path = Path(tmpdir / "data.zarr")
    meta, _, _ = split_channels(dat_path)
    ref_jso = metadata_to_jso(meta)

    dat_to_zarr(dat_path, out_path)
    container = zarr.open(out_path, "r")
    assert_metadata_contains_values(container.attrs, ref_jso)
    test_bytes = write_header(container.attrs)

    ref_bytes = read_header_bytes(dat_path)
    assert test_bytes == ref_bytes


def test_meta_jso_roundtrip_n5(dat_path, tmpdir):
    out_path = Path(tmpdir / "data.zarr")
    meta, _, _ = split_channels(dat_path)
    ref_jso = metadata_to_jso(meta)

    dat_to_n5(dat_path, out_path)
    container = zarr.open(zarr.N5Store(out_path), "r")
    assert_metadata_contains_values(container.attrs, ref_jso)

    test_bytes = write_header(container.attrs)

    ref_bytes = read_header_bytes(dat_path)
    assert test_bytes == ref_bytes


def test_meta_jso_roundtrip(dat_path):
    ref, _, _ = split_channels(dat_path)
    meta_jso = metadata_to_jso(ref)
    test = metadata_to_numpy(meta_jso)

    for k, ref_v in ref.items():
        if k.startswith("_"):
            continue
        test_v = test[k]
        if isinstance(ref_v, bytes):
            assert test_v == ref_v
        else:
            assert np.allclose(test_v, ref_v)


@pytest.mark.parametrize("mode", ["hdf5", "n5", "zarr"])
def test_roundtrip(dat_path, tmpdir, mode):
    if mode == "hdf5":
        to_container = dat_to_hdf5
        from_container = hdf5_to_bytes
    elif mode == "n5":
        to_container = dat_to_n5
        from_container = n5_to_bytes
    elif mode == "zarr":
        to_container = dat_to_zarr
        from_container = zarr_to_bytes
    else:
        raise ValueError(f"Unknown mode '{mode}'")

    out_path = Path(tmpdir / f"data.{mode}")
    to_container(dat_path, out_path)
    written_bytes = from_container(out_path)
    orig_bytes = dat_path.read_bytes()
    assert len(written_bytes) == len(orig_bytes)
    assert md5sum(written_bytes) == md5sum(orig_bytes)
