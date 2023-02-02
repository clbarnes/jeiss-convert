# jeiss-convert

Losslessly convert Jeiss .dat files into a well-documented, widely compatible format: HDF5.

The goal of the project is to be the single piece of software which ever has to read Jeiss .dat files.
Image your sample, run this script, and never think about the original .dat again.
Additionally benefit from self-documenting metadata (including enums), separated channels, ISO-8601 dates, multiple images per file, and optionally compression and corruption detection.

Other processing steps, such as dropping channels, rescaling values, and more complex tasks such as contrast correction and stack alignment, are out of scope for this package and should target the HDF5s produced here.

## Installation

Install from GitHub using pip:

```sh
pip install git+https://github.com/clbarnes/jeiss-convert.git
```

This will make the below command line scripts and the `jeiss_convert` package available in your current python environment.
Preferably, specify a particular revision for pip to use.

Consider using [pipx](https://pypa.github.io/pipx/) if you need the tool available outside of a virtual environment.

Alternatively, you can clone the repository and install locally:

```sh
git clone https://github.com/clbarnes/jeiss-convert.git
cd jeiss-convert
pip install .
```

## Usage

Some metadata are integers which represent enumerated values (enums).
By default, `jeiss-convert` associates the metadata key with the integer value,
and additionally stores the meaning of the value under the same key suffixed with `__name` (note the double underscore).
e.g. `{"Mode": 5}` in the `.dat` would be represented as
`{"Mode": 5, "Mode__name": "SEM Drift Correction"}` in the output.

Additionally, date fields (listed and serialised according to the format specified in `jeiss-specs/misc.toml`) will be duplicated in ISO-8601 form with the key suffix `__iso` (note the double underscore):
e.g. `{"SWdate": "02/01/2023"}` (ambiguous, locale-dependent, not sortable) would be represented as
`{"SWdate": "02/01/2023", "SWdate__iso": "2023-01-02"}` (internationally standardised) in the output.

Jeiss microscopes can output CSV files with additional metadata.
This metadata can be stored as attributes on an empty group in the output HDF5,
so long as the correct row can be found based on the .dat file's acquisition date.
This can be given explicitly or parsed from file path.
Again, the non-standard `Date` field and the `Time` field are used to create an additional
`Datetime__iso` field.

### `dat2hdf5`

```_dat2hdf5
usage: dat2hdf5 [-h] [-m] [-c CHUNKS] [-z COMPRESSION] [-B] [-o] [-f]
                [--csv-path CSV_PATH] [--datetime DATETIME]
                [--datetime-pattern DATETIME_PATTERN] [--store-name]
                [--fill FILL] [--version]
                dat hdf5 [group]

Convert a Jeiss FIBSEM .dat file into a standard HDF5 group (which may be the
container's root), preserving all known metadata as group attributes.
Additionally stores the raw header and footer bytes as uint8 arrays (under
keys "_header" and "_footer" respectively), the version string of the
conversion tool ("_dat2hdf5_version"). If the full contents of the .dat were
written to HDF5 successfully, the field "_conversion_complete" will exist and
be True. The length of the original .dat file is stored in "_dat_nbytes", and
its filename or path can optionally be written in "_dat_filename". Each
channel which exists is stored as a dataset within the group named "AI1",
"AI2", ..., based on the original base-1 channel index ("AI" stands for
"Analogue Input"). Channel datasets optionally store the minimum and maximum
values as attributes "min" and "max". Datasets may optionally be chunked,
compressed, and/or have other filters applied. Lastly, additional metadata
from a CSV indexed by acquisition date and time can be included as attributes
on an empty "additional_metadata" subgroup.

positional arguments:
  dat                   Path to a .dat file
  hdf5                  Path to HDF5 file; may exist
  group                 HDF5 group within the given file; must not exist. If
                        not given, use the root.

options:
  -h, --help            show this help message and exit
  -m, --minmax          Calculate each array's min and max values and store as
                        attributes
  -c CHUNKS, --chunks CHUNKS
                        Chunking scheme (default none) as a single integer for
                        a square chunk, comma-separated integers in XY, or
                        'auto' for automatic.
  -z COMPRESSION, --compression COMPRESSION
                        Compression to use (default none); should be 'lzf' or
                        'gzip'. Gzip can be suffixed with the level 0-9.
  -B, --byte-shuffle    Apply the byte shuffle filter, which may decrease size
                        of compressed data.
  -o, --scale-offset    Apply the scale-offset filter, which may decrease size
                        of chunked data.
  -f, --fletcher32      Checksum each chunk to allow detection of corruption
  --csv-path CSV_PATH, -p CSV_PATH
                        Path to metadata CSV. Must be paired with either
                        --datetime (-d) or --datetime-pattern (-D) so that the
                        file can be matched to an entry.
  --datetime DATETIME, -d DATETIME
                        Acquisition datetime in ISO-8601 format; only used to
                        match file to its entry in a metadata CSV. Mutually
                        exclusive with --datetime-pattern (-D).
  --datetime-pattern DATETIME_PATTERN, -D DATETIME_PATTERN
                        Dfregex (i.e. regex plus C-like date/time codes)
                        showing how to parse the acquisition date and time
                        from the given file path; only used to match file to
                        its entry in a metadata CSV. See here for more
                        details: https://github.com/stephen-
                        zhao/datetime_matcher#dfregex-syntax-informal-spec .
                        Mutually exclusive with --datetime (-d).
  --store-name, -n      Store dat's filename in resulting HDF5 group metadata
                        under '_dat_filename'.If used twice, store the given
                        path. If used three times, store the absolute path.
  --fill FILL, -F FILL  If a file is truncated in the image section, fill it
                        with this value (must be valid for the file's data
                        type). If not given, raise an error on truncated
                        files.
  --version             show program's version number and exit
```

### `dat2hdf5-verify`

```_dat2hdf5-verify
usage: dat2hdf5-verify [-h] [-d] [-s] [--write-dat] [--version]
                       dat hdf5 [group]

Verify that the contents of an HDF5 container are identical to an existing
Jeiss FIBSEM .dat file, so that the .dat can be safely deleted.

positional arguments:
  dat               Path to a .dat file
  hdf5              Path to HDF5 file; may exist
  group             HDF5 group within the given file, default root; otherwise
                    must not exist

options:
  -h, --help        show this help message and exit
  -d, --delete-dat  Delete the .dat file if the check succeeds
  -s, --strict      Check for identity of bytes rather than hash (slow and
                    unnecessary)
  --write-dat       Instead of checking the HDF5 for its identity with an
                    existing dat, write out the calculated dat. Comes with an
                    interactive warning. Don't do this.
  --version         show program's version number and exit
```

### `datmeta`

```_datmeta
usage: datmeta [-h] {ls,fmt,json,get} ...

Interrogate and dump Jeiss FIBSEM .dat metadata.

options:
  -h, --help         show this help message and exit

subcommands:
  {ls,fmt,json,get}
```

#### `datmeta ls`

```_datmeta-ls
usage: datmeta ls [-h] dat

List metadata field names.

positional arguments:
  dat         Path to .dat file

options:
  -h, --help  show this help message and exit
```

#### `datmeta fmt`

```_datmeta-fmt
usage: datmeta fmt [-h] dat [format ...]

Use python format string notation to interpolate metadata values into string.
If multiple format strings are given, print each separated by newlines.

positional arguments:
  dat         Path to .dat file
  format      Format string, e.g. 'Version is {FileVersion}'. More details at
              https://docs.python.org/3.10/library/string.html#formatstrings.

options:
  -h, --help  show this help message and exit
```

#### `datmeta json`

```_datmeta-json
usage: datmeta json [-h] [-s] [-i INDENT] dat [field ...]

Dump metadata as JSON.

positional arguments:
  dat                   Path to .dat file
  field                 Only dump the listed fields.

options:
  -h, --help            show this help message and exit
  -s, --sort            Sort JSON keys
  -i INDENT, --indent INDENT
                        Number of spaces to indent. If negative, also strip
                        spaces between separators.
```

#### `datmeta get`

```_datmeta-get
usage: datmeta get [-h] [-d] dat [field ...]

Read metadata values. By default, a TSV with keys in the first column and
values in the second (arrays JSON-serialised); key column can be omitted.

positional arguments:
  dat              Path to .dat file
  field            Only show the given fields

options:
  -h, --help       show this help message and exit
  -d, --data-only  Do not print field names
```

### Use as a library

Avoid reading data directly from .dat files where possible.
Use the scripts provided by this package to convert the data into HDF5 and base the rest of your tooling around that.

If your conversion is more easily handled from python, as part of a more complex pipeline, you can use the provided `jeiss_convert.dat_to_hdf5` function.

For example, to write all .dat files in a directory into a single HDF5 file (one group per file, with the group name based on the filename):

```python
from pathlib import Path

from jeiss_convert import dat_to_hdf5

DAT_ROOT = Path("path/to/dat/dir").resolve()
HDF5_PATH = Path("path/to/container.hdf5").resolve()

DS_KWARGS = {
    "chunks": True,  # automatically chunk datasets
    "compression": "gzip",  # compress data at default level
}

for dat_path in sorted(DAT_ROOT.glob("*.dat")):
    group_name = dat_path.stem
    dat_to_hdf5(dat_path, HDF5_PATH, group_name, ds_kwargs=DS_KWARGS)
```

Or, to recursively discover .dat files in a directory and write each into the root of a separate HDF5 file, in parallel:

```python
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

from jeiss_convert import dat_to_hdf5

N_PROCESSES = 10

DAT_ROOT = Path("path/to/dat/dir").resolve()
HDF5_ROOT = Path("path/to/hdf5/dir").resolve()

DS_KWARGS = {
    "chunks": True,  # automatically chunk dataset
    "compression": "gzip",  # compress data at default level
}


def worker_fn(dat_path: Path):
    # HDF5 file to be written to the same relative location
    # in the target directory as it was in the source directory
    sub_path = dat_path.relative_to(DAT_ROOT)
    hdf5_path = (HDF5_ROOT / sub_path).with_suffix(".hdf5")

    # ensure that all ancestor directories exist
    hdf5_path.parent.mkdir(parents=True, exist_ok=True)

    return dat_to_hdf5(
        dat_path,
        hdf5_path,
        ds_kwargs=DS_KWARGS,
    )


with ProcessPoolExecutor(N_PROCESSES) as p:
    for _ in p.map(
        worker_fn,
        DAT_ROOT.glob("**/*.dat"),  # recursively look for .dat files
    ):
        pass
```

Jeiss microscopes can generate CSV files containing additional metadata.
These can be matched to a .dat file based on the acquisition date and time.

This package contains helper methods for matching a .dat's acquisition datetime to a row of a `pandas.DataFrame` representing these CSVs.
DataFrames must have string `"Date"` and `"Time"` columns
in `dd/mm/YYYY` and `HH:MM:SS` format respectively.

```python
import datetime as dt
from pathlib import Path

import pandas as pd
from jeiss_convert import dat_to_hdf5, get_csv_metadata, datetime_from_path

dat_path = Path("path/to/data_2023-01-24_172320_0-0-0.dat")
metadata = pd.read_csv(Path("path/to/metadata.csv"))

acquisition_datetime = datetime_from_path(
    dat_path,
    # Dfregex pattern for parsing datetime from file path
    r".*/data_%Y-%m-%d_%H%M%S_\d+-\d+-\d+\.dat$",
)

meta = get_csv_metadata(
    metadata,
    acquisition_datetime,  # used to find correct row
)

dat_to_hdf5(
    dat_path,
    ...,  # other args
    additional_metadata=meta,
)
```

## Containerisation

This package can be containerised with the included [Apptainer](https://apptainer.org/) recipe.
Use `make container` on linux (requires sudo) to create an image file `jeiss_convert.sif`.
This file can be moved to any computer with the apptainer runtime installed, and executed with `apptainer exec jeiss_convert.sif <your_command>`, e.g `apptainer exec jeiss_convert.sif dat2hdf5 --version`.

Depending on which directories you need to access, you may need to execute with [bind mounts](https://apptainer.org/docs/user/main/bind_paths_and_mounts.html#user-defined-bind-paths).

## Contributing

### Jeiss specifications

Modifications to the Jeiss .dat spec should be contributed to the [jeiss-specs](https://github.com/clbarnes/jeiss-specs) project.

### Testing

Tests can be run (using `pytest`) with `make test`.

`jeiss-specs` contains sample headers for some specification versions.
It also includes URLs where full `.dat` files can be downloaded (which will be handled automatically),
but these are large and slow to download.

Tests requiring full `.dat` files can be skipped with `make test-skipfull` (or `pytest --skip-full`).

By default all tests run against all versions, and skip where test files are not available.

### Non-goals

Pull requests implementing a public-facing API for reading data from .dat files directly will likely not be accepted.

This package is not intended to make it easy to read .dat files.
It is intended to ensure that .dat files are read exactly once:
so that they can be converted to a widely-supported, well-documented, self-documenting format (HDF5),
and then deleted.
