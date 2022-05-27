import csv
from pathlib import Path

import pooch
import pytest

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


@pytest.fixture(params=versions)
def dat_path(request, sample_dats):
    version = request.param
    if version not in sample_dats:
        pytest.skip(f"No sample file for version {version}")

    md5sum, url = sample_dats[version]
    return pooch.retrieve(url=url, known_hash="md5:" + md5sum)
