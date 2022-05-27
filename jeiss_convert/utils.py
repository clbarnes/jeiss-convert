import typing as tp
from io import BytesIO
from pathlib import Path

import h5py
import numpy as np

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


def dat_to_hdf5(
    dat_path: Path,
    hdf5_path: Path,
    hdf5_group=None,
    ds_kwargs=None,
):
    if ds_kwargs is None:
        ds_kwargs = dict()

    if hdf5_group is None:
        hdf5_group = "/"

    all_data = ParsedData.from_file(dat_path)

    ds_to_channel = dict()
    max_channel = 0
    for input_id in range(1, 5):
        ds = f"AI{input_id}"

        if all_data.meta[ds]:
            ds_to_channel[ds] = max_channel
            max_channel += 1

    with h5py.File(hdf5_path, "a") as h5:
        if hdf5_group == "/":
            g = h5
        else:
            g = h5.create_group(hdf5_group)

        g.attrs.update(all_data.meta)
        g.attrs["_header"] = np.frombuffer(all_data.header, dtype="uint8")
        g.attrs["_footer"] = np.frombuffer(all_data.footer, dtype="uint8")
        for ds, channel_idx in ds_to_channel.items():
            g.create_dataset(ds, data=all_data.data[channel_idx], **ds_kwargs)


def hdf5_to_bytes(hdf5_path, hdf5_group=None):
    if hdf5_group is None:
        hdf5_group = "/"

    with h5py.File(hdf5_path) as h5:
        g = h5[hdf5_group]
        header = write_header(g.attrs)
        to_stack = []
        for input_id in range(1, 5):
            ds_name = f"AI{input_id}"
            if ds_name not in g:
                continue
            to_stack.append(g[ds_name][:])
        footer = g.attrs.get("_footer", np.array([], "uint8"))

    stacked = np.stack(to_stack, axis=0)
    dtype = stacked.dtype.newbyteorder(DEFAULT_BYTE_ORDER)
    b = np.asarray(stacked, dtype, order="F").tobytes(order="F")
    footer_bytes = footer.tobytes()
    return header + b + footer_bytes
