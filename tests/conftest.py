import csv
from pathlib import Path

import pooch
import pytest

project_dir = Path(__file__).resolve().parent.parent
spec_dir = project_dir / "jeiss_convert" / "jeiss-specs"
versions = [int(p.stem[1:]) for p in spec_dir.glob("specs/*.tsv") if p.stem != "v0"]
meta_paths = {int(p.stem[1:]): p for p in spec_dir.glob("example_metadata/*.dat")}


def pytest_addoption(parser):
    parser.addoption(
        "--skip-full",
        action="store_true",
        help="Skip tests which require full .dat files",
    )


@pytest.fixture(scope="session")
def sample_dats():
    tsv = spec_dir / "example_files.tsv"
    out = dict()
    with open(tsv) as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            out[int(row["version"])] = (row["md5sum"], row["url"])
    return out


@pytest.fixture(params=versions)
def dat_path(request, sample_dats):
    if request.config.getoption("--skip-full"):
        pytest.skip("Requires full .dat file, --skip-large given")

    version = request.param
    if version not in sample_dats:
        pytest.skip(f"No sample file for version {version}")

    md5sum, url = sample_dats[version]

    return Path(pooch.retrieve(url=url, known_hash="md5:" + md5sum))


@pytest.fixture(params=versions)
def meta_path(request):
    version = request.param

    path = meta_paths.get(version)

    if path is None:
        pytest.skip(f"No sample metadata file for version {version}")

    return path
