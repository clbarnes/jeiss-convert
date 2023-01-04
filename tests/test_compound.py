from jeiss_convert.misc import HEADER_LENGTH
from jeiss_convert.compound import Header
import h5py


def test_header_roundtrip(dat_path):
    with open(dat_path, "rb") as f:
        ref_bytes = f.read(HEADER_LENGTH)
    header = Header.from_file(dat_path)
    test_bytes = header.to_bytes()
    assert test_bytes == ref_bytes


def test_jso_roundtrip(dat_path):
    ref_header = Header.from_file(dat_path)
    ref_jso = ref_header.to_dict(is_jso=True)
    test_header = Header.from_dict(ref_jso, is_jso=True)
    assert test_header == ref_header


def test_hdf5_roundtrip(dat_path, tmp_path):
    ref_header = Header.from_file(dat_path)
    h5path = tmp_path / "data.hdf5"
    with h5py.File(h5path, "a") as f:
        ref_header.to_hdf5(f, "header")
        test_header = Header.from_hdf5(f["header"])

    assert test_header == ref_header
