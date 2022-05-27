# jeiss-convert

Convert Jeiss .dat files

## Usage

```_dat2hdf5
usage: dat2hdf [-h] [-c CHUNKS] [-z COMPRESSION] dat hdf5 [group]

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
```

```_dat2hdf5-verify
usage: dat2hdf-verify [-h] [-d] dat hdf5 [group]

positional arguments:
  dat               Path to a .dat file
  hdf5              Path to HDF5 file; may exist
  group             HDF5 group within the given file, default root; otherwise
                    must not exist

optional arguments:
  -h, --help        show this help message and exit
  -d, --delete-dat  Delete the .dat file if the check succeeds
```
