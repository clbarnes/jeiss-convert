# jeiss-convert

Convert Jeiss .dat files

## Usage

### `dat2hdf5`

```_dat2hdf5
usage: dat2hdf5 [-h] [-c CHUNKS] [-z COMPRESSION] [-B] [-o] [-f] [--version]
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

Read metadata values.

positional arguments:
  dat              Path to .dat file
  field            Only show the given fields

optional arguments:
  -h, --help       show this help message and exit
  -d, --data-only  Do not print field names
```
