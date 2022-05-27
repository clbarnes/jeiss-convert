from pathlib import Path

from jeiss_convert import convert, verify


def test_importable():
    import jeiss_convert

    assert jeiss_convert.__version__


def test_convert_verify(dat_path, tmpdir):
    hdf5_path = Path(tmpdir / "data.hdf5")
    status = convert.main([str(dat_path), str(hdf5_path)])
    assert status == 0
    assert hdf5_path.is_file()
    verified = verify.main([str(dat_path), str(hdf5_path)])
    assert verified == 0
