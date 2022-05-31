from pathlib import Path

from jeiss_convert import convert, verify


def test_importable():
    import jeiss_convert

    assert jeiss_convert.__version__


def test_convert_verify(dat_path, tmpdir):
    hdf5_path = Path(tmpdir / "data.hdf5")
    conv_status = convert.main([str(dat_path), str(hdf5_path)])
    assert conv_status == 0
    assert hdf5_path.is_file()
    verif_status = verify.main([str(dat_path), str(hdf5_path)])
    assert verif_status == 0
