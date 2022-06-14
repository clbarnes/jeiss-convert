import typing as tp
from io import BytesIO
from pathlib import Path

import h5py
import numpy as np
from .version import version

spec_dir = Path(__file__).resolve().parent / "jeiss-specs" / "specs"

DEFAULT_AXIS_ORDER = "F"
DEFAULT_BYTE_ORDER = ">"
HEADER_LENGTH = 1024


def read_value(
    buffer: bytes,
    dtype: np.dtype,
    offset: int = 0,
    shape: tp.Optional[tuple[int, ...]] = None,
):
    if not shape:
        reshape = None
        count = 1
    else:
        try:
            reshape = tuple(shape)
            count = np.prod(reshape)
        except TypeError:
            count = shape
            reshape = None

    data = np.frombuffer(buffer, dtype, count, offset=offset)
    if len(data) < count:
        raise RuntimeError(f"Count not read {count} items from byte {offset}")
    if not reshape:
        return data[0]
    return data.reshape(reshape, order=DEFAULT_AXIS_ORDER)


class SpecTuple(tp.NamedTuple):
    name: str
    dtype: np.dtype
    offset: int
    shape: tp.Optional[tuple[tp.Union[int, str], ...]]

    def realise_shape(self, meta: dict[str, int]) -> tp.Optional[tuple[int]]:
        if not self.shape or self.shape == (0,):
            return None

        out = []
        for item in self.shape:
            if isinstance(item, int):
                out.append(item)
            else:
                out.append(meta[item])
        return tuple(out)

    @classmethod
    def from_line(cls, line: str):
        items = line.strip().split("\t")
        shape = []
        for item in items[3].split(","):
            item = item.strip()
            try:
                shape.append(int(item))
            except ValueError:
                shape.append(item)

        return cls(items[0], np.dtype(items[1]), int(items[2]), tuple(shape))

    @classmethod
    def from_file(cls, path, skip_header=True):
        with open(path) as f:
            if skip_header:
                next(f)
            for line in f:
                yield cls.from_line(line)

    def read_into(self, f, out=None):
        if out is None:
            out = dict()
        if self.name not in out:
            out[self.name] = read_value(
                f, self.dtype, self.offset, self.realise_shape(out)
            )
        return out


SPECS = {
    int(tsv.stem[1:]): tuple(SpecTuple.from_file(tsv)) for tsv in spec_dir.glob("*.tsv")
}


def _parse_with_version(b: bytes, version: int):
    spec = SPECS[version]
    out = dict()
    for line in spec:
        line.read_into(b, out)
    return out


def parse_bytes(b: bytes):
    d = _parse_with_version(b, 0)
    return _parse_with_version(b, d["FileVersion"])


def parse_file(fpath: Path):
    with open(fpath, "rb") as f:
        b = f.read(HEADER_LENGTH)
        return parse_bytes(b)


def write_header(data: dict[str, tp.Any]):
    buffer = BytesIO(b"\0" * HEADER_LENGTH)
    for name, dtype, offset, _ in SPECS[data["FileVersion"]]:
        item = data[name]
        if not isinstance(item, np.ndarray):
            item = np.asarray(item, dtype=dtype, order=DEFAULT_AXIS_ORDER)
        b = item.tobytes(DEFAULT_AXIS_ORDER)
        buffer.seek(offset)
        buffer.write(b)

    return buffer.getvalue()


class ParsedData(tp.NamedTuple):
    meta: dict[str, tp.Any]
    data: np.ndarray
    header: tp.Optional[bytes] = None
    footer: tp.Optional[bytes] = None

    @classmethod
    def from_bytes(cls, b: bytes):
        meta = parse_bytes(b)
        header = b[:HEADER_LENGTH]
        shape = (meta["ChanNum"], meta["XResolution"], meta["YResolution"])
        dtype = np.dtype("u1" if meta["EightBit"] else ">i2")
        data = read_value(b, dtype, HEADER_LENGTH, shape)
        footer = b[int(HEADER_LENGTH + np.prod(shape) * dtype.itemsize) :]
        return cls(meta, data, header, footer)

    @classmethod
    def from_file(cls, fpath):
        with open(fpath, "rb") as f:
            return cls.from_bytes(f.read())

