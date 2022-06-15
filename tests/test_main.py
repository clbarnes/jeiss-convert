from pathlib import Path

import pytest

from jeiss_convert import convert, verify
from jeiss_convert.hdf5 import dat_to_hdf5, hdf5_to_bytes
from jeiss_convert.utils import md5sum
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
    assert md5sum(orig_bytes) == md5sum(written_bytes)
