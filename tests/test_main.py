from contextlib import contextmanager
from pathlib import Path

import h5py
import numpy as np
import zarr

from jeiss_convert.misc import FOOTER_KEY, HEADER_LENGTH
from jeiss_convert.utils import (
    into_bytes,
    md5sum,
    metadata_to_jso,
    metadata_to_numpy,
    parse_file,
    split_channels,
    write_header,
)

from .conftest import Mode, RoundtripResult


def test_importable():
    import jeiss_convert

    assert jeiss_convert.__version__


def test_can_write(dat_path, mode, tmp_path):
    container_path = tmp_path / f"data.{mode.name}"
    mode.dat_to_container(dat_path, container_path)
    assert container_path.exists()


def test_can_reconvert_written(dat_path, mode, tmp_path):
    container_path = tmp_path / f"data.{mode.name}"
    mode.dat_to_container(dat_path, container_path)
    written_bytes = mode.container_to_dat_bytes(container_path)
    assert len(written_bytes)


# def test_cli_convert_verify(dat_path, tmp_path):
#     hdf5_path = Path(tmp_path / "data.hdf5")
#     conv_status = convert.main([str(dat_path), str(hdf5_path)])
#     assert conv_status == 0
#     assert hdf5_path.is_file()
#     verif_status = verify.main([str(dat_path), str(hdf5_path)])
#     assert verif_status == 0


def assert_arrays_equal(test: np.ndarray, ref: np.ndarray):
    # assert test.dtype == ref.dtype
    assert test.shape == ref.shape
    assert test.ravel()[0] == ref.ravel()[0]
    assert np.allclose(test, ref)


def assert_channel_arrays_equal(
    test: dict[str, np.ndarray], ref: dict[str, np.ndarray]
):
    assert set(test) == set(ref)
    for key, a_val in test.items():
        assert_arrays_equal(a_val, ref[key])


def channel_dict(names, data) -> dict[str, np.ndarray]:
    d = {cn: data[idx] for idx, cn in enumerate(names)}
    return d


def test_array_roundtrip(roundtripped: RoundtripResult):
    dat_path, container_path, _, _ = roundtripped

    _, channel_names, data = split_channels(dat_path)
    dat_arrays = channel_dict(channel_names, data)

    with open_root(container_path) as f:
        for cn in channel_names:
            dat_arr = dat_arrays[cn]
            written_arr = f[cn][:]

            assert_arrays_equal(written_arr, dat_arr)
            # assert_bytes_equal(into_bytes(written_arr), into_bytes(dat_arr))


def assert_bytes_equal(test: bytes, ref: bytes, ends=64, test_full=False):
    assert len(test) == len(ref)
    assert test[:ends] == ref[:ends]
    assert test[ends:] == ref[ends:]
    assert md5sum(test) == md5sum(ref)
    if test_full:
        assert test == ref


def assert_metadata_contains_values(test, ref):
    """test must be superset of ref.
    test must contain vals coercible into dtypes of ref"""
    for k, ref_v in ref.items():
        if k.startswith("_"):
            continue
        assert k in test
        test_v = test[k]
        assert test_v == ref_v


def read_header_bytes(path):
    with open(path, "rb") as f:
        return f.read(HEADER_LENGTH)


def test_header_roundtrip(roundtripped: RoundtripResult):
    dat_path, container_path, _, json_metadata = roundtripped
    meta = parse_file(dat_path)
    ref_jso = metadata_to_jso(meta)

    with open_root(container_path) as f:
        test_jso = f.attrs
        if not json_metadata:
            test_jso = metadata_to_jso(test_jso)

        test_bytes = write_header(f.attrs)

        assert_metadata_contains_values(test_jso, ref_jso)

    ref_bytes = read_header_bytes(dat_path)
    assert test_bytes == ref_bytes


def test_meta_jso_roundtrip(dat_path):
    ref = parse_file(dat_path)
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

    assert write_header(test) == read_header_bytes(dat_path)


@contextmanager
def open_root(container_path: Path):
    mode = container_path.suffix
    if mode.endswith("hdf5"):
        with h5py.File(container_path, "r") as f:
            yield f
    elif mode.endswith("zarr"):
        yield zarr.open(container_path, "r")
    elif mode.endswith("n5"):
        yield zarr.open(zarr.N5Store(container_path), "r")
    else:
        raise ValueError(f"Unknown mode '{mode}'")


def test_footer_roundtrip(roundtripped: RoundtripResult):
    dat_path, container_path, written_bytes, _ = roundtripped

    stored_footer = None

    with open_root(container_path) as g:
        stored_footer = into_bytes(g.attrs[FOOTER_KEY])

    if stored_footer is None:
        raise ValueError("Could not read test footer")

    dat_bytes = dat_path.read_bytes()
    dat_tail = dat_bytes[-len(stored_footer) :]
    assert_bytes_equal(stored_footer, dat_tail)
    written_tail = written_bytes[-len(stored_footer) :]
    assert_bytes_equal(written_tail, dat_tail)


def test_roundtrip(dat_path, tmp_path, mode: Mode):
    out_path = Path(tmp_path / f"data.{mode}")
    mode.dat_to_container(dat_path, out_path)
    written_bytes = mode.container_to_dat_bytes(out_path)
    orig_bytes = dat_path.read_bytes()
    assert_bytes_equal(written_bytes, orig_bytes)
