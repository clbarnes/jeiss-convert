# jeiss-convert

Convert Jeiss .dat files

## Usage

```_dat2hdf5
usage: dat2hdf [-h] [-c CHUNKS] [-z COMPRESSION] [-B] [-o] [-f]
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
                        Chunking scheme (default none) as comma-separated
                        integers in XY, or 'auto' for automatic.
  -z COMPRESSION, --compression COMPRESSION
                        Compression to use (default none); should be 'lzf' or
                        'gzip'. Gzip can be suffixed with the level 0-9.
  -B, --byteshuffle     Apply the byteshuffle filter, which may decrease size
                        of compressed data.
  -o, --scale-offset    Apply the scale-offset filter, which may decrease size
                        of chunked data.
  -f, --fletcher32      Checksum each chunk to allow detection of corruption
```

```_dat2hdf5-verify
usage: dat2hdf-verify [-h] [-d] [-s] [--write-dat] dat hdf5 [group]

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
```
