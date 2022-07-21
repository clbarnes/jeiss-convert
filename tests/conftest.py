import csv
import shutil
from pathlib import Path
from typing import Callable, NamedTuple

import pooch
import pytest

from jeiss_convert.hdf5 import dat_to_hdf5, hdf5_to_bytes
from jeiss_convert.zr import dat_to_n5, dat_to_zarr, n5_to_bytes, zarr_to_bytes

project_dir = Path(__file__).resolve().parent.parent
spec_dir = project_dir / "jeiss_convert" / "jeiss-specs"
versions = [
    int(p.stem[1:]) for p in (spec_dir / "specs").glob("*.tsv") if p.stem != "v0"
]


@pytest.fixture(scope="session")
def sample_dats():
    tsv = spec_dir / "example_files.tsv"
    out = dict()
    with open(tsv) as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            out[int(row["version"])] = (row["md5sum"], row["url"])
    return out


@pytest.fixture(params=versions, scope="session")
def dat_path(request, sample_dats):
    version = request.param
    if version not in sample_dats:
        pytest.skip(f"No sample file for version {version}")

    md5sum, url = sample_dats[version]
    return Path(pooch.retrieve(url=url, known_hash="md5:" + md5sum))


class Mode(NamedTuple):
    name: str
    dat_to_container: Callable
    container_to_dat_bytes: Callable
    json_metadata: bool


@pytest.fixture(params=["hdf5", "n5", "zarr"])
def mode(request):
    if request.param == "hdf5":
        return Mode("hdf5", dat_to_hdf5, hdf5_to_bytes, False)
    elif request.param == "n5":
        return Mode("n5", dat_to_n5, n5_to_bytes, True)
    elif request.param == "zarr":
        return Mode("zarr", dat_to_zarr, zarr_to_bytes, True)
    else:
        raise ValueError("Unknown mode name")


class RoundtripResult(NamedTuple):
    dat_path: Path
    container_path: Path
    written_bytes: bytes
    json_metadata: bool


@pytest.fixture
def roundtripped(dat_path, mode, tmp_path):
    container_path = tmp_path / f"data.{mode.name}"
    mode.dat_to_container(dat_path, container_path)
    written_bytes = mode.container_to_dat_bytes(container_path)
    return RoundtripResult(dat_path, container_path, written_bytes, mode.json_metadata)
