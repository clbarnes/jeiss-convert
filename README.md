# jeiss-convert

Convert Jeiss .dat files into a well-documented, widely compatible format: HDF5.

The goal of the project is to be the single piece of software which ever has to read Jeiss .dat files.
Image your sample, run this script, and never think about the original .dat again.

## Installation

Install from GitHub using pip:

    pip install git+https://github.com/clbarnes/jeiss-convert.git

This will make the below command line scripts and the `jeiss_convert` package available in your current python environment.
Preferably, specify a particular revision for pip to use.

Consider using [pipx](https://pypa.github.io/pipx/) if you need the tool available outside of a virtual environment.

Alternatively, you can clone the repository and install locally:

    git clone https://github.com/clbarnes/jeiss-convert.git
    cd jeiss-convert
    pip install .

## Usage

### `dat2hdf5`

```_dat2hdf5
usage: dat2hdf5 [-h] [-m] [-c CHUNKS] [-z COMPRESSION] [-B] [-o] [-f]
                [--version]
                dat hdf5 [group]

Convert a Jeiss FIBSEM .dat file into a standard HDF5, preserving all known
metadata as group attributes, as well as storing the raw header and footer
bytes.

positional arguments:
  dat                   Path to a .dat file
  hdf5                  Path to HDF5 file; may exist
  group                 HDF5 group within the given file; must not exist

optional arguments:
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

optional arguments:
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

optional arguments:
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

optional arguments:
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
              https://docs.python.org/3.9/library/string.html#formatstrings.

optional arguments:
  -h, --help  show this help message and exit
```

#### `datmeta json`

```_datmeta-json
usage: datmeta json [-h] [-s] [-i INDENT] dat [field ...]

Dump metadata as JSON.

positional arguments:
  dat                   Path to .dat file
  field                 Only dump the listed fields.

optional arguments:
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

optional arguments:
  -h, --help       show this help message and exit
  -d, --data-only  Do not print field names
```

### Use as a library

Avoid reading data directly from .dat files where possible.
Use the scripts provided by this package to convert the data into HDF5 and base the rest of your tooling around that.

If your conversion is more easily handled from python, as part of a more complex pipeline, you can use the provided `jeiss_convert.dat_to_hdf5` function.
For example, to discover .dat files in a directory and write them elsewhere, in parallel:

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
    p.map(
        worker_fn,
        DAT_ROOT.glob("**/*.dat"),  # recursively look for .dat files
    )
```

## Containerisation

This package can be containerised with the included [Apptainer](https://apptainer.org/) recipe.
Use `make container` on linux (requires sudo) to create an image file `jeiss_convert.sif`.
This file can be moved to any computer with the apptainer runtime installed, and executed with `apptainer exec jeiss_convert.sif <your_command>`, e.g `apptainer exec jeiss_convert.sif dat2hdf5 --version`.

Depending on which directories you need to access, you may need to execute with [bind mounts](https://apptainer.org/docs/user/main/bind_paths_and_mounts.html#user-defined-bind-paths).

## Contributing

Modifications to the Jeiss .dat spec should be contributed to the [jeiss-specs](https://github.com/clbarnes/jeiss-specs) project.
