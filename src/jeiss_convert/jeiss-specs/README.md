# jeiss-specs

Specifications, in TSV format, of the metadata in the header of `.dat` files produced by "Jeiss" Focused Ion Beam Scanning Electron Microscopes.

## General notes

- Arrays are in column-major ("Fortran") order.
- Multi-byte data is in big-endian byte order, little-endian bit order.
- Date is stored as `DD/MM/YYYY`, for some reason.
- `specs/v0.tsv` is not a spec in its own right, but a core metadata common across all versions. In some cases, these fields determine the size of later metadata fields, so it's convenient to parse this first.
- The image data begins at offset 1024, and has shape (`ChanNum`, `XResolution`, `YResolution`).
- There may be a binary footer of indeterminate length, after the image data.

## dtype

Field data types are encoded as 3+ characters:

- `>` for big-endian or `<` for little-endian byte order. All data types here are `>`, but it is included to be explicit. Note this is irrelevant for single-byte types (`S` and `u1`), but included anyway.
- A letter for the data type: `f`loat, `i`nteger, `u`nsigned integer, `S`tring (ASCII, right-padded with null bytes).
- An integer for how long the type is, in bytes.

This representation is based on the NumPy [Array Interface](https://numpy.org/doc/stable/reference/arrays.interface.html#object.__array_interface__)'s typestrs.

Some `>u1` fields represent booleans, where 0 is False and anything else is True.

### Enums

Some integer fields represent enums.
`enums/${FIELD_NAME}.tsv` enumerate the integer values and the enums they represent.

## shape

`0` represents a single element (where `1` would represent a 1-length array).
For multidimensional arrays, the length of each dimension is separated by a comma.
In some versions, the shape depends on the value of an earlier field: in that case, the name of the field is used instead of an integer.

## Example files

For testing purposes, `example_files.tsv` lists publicly-accessible URLs to `.dat` files for specific versions.

The TSV lists the version number, the hex digest of the MD5 hashsum of the file, and a public URL to the file.

## Attribution

These specs were generated from Davis Bennett's [fibsem-tools](https://github.com/janelia-cosem/fibsem-tools).
Thanks also to Mark Kittisopikul for his work on sanitising the format,
and to Shan Xu and the Hess lab for their creation of the Jeiss FIBSEM.
