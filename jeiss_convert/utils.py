import hashlib
import logging
import sys
import typing as tp
from io import BytesIO
from pathlib import Path

import numpy as np

from .misc import (
    DEFAULT_AXIS_ORDER,
    DEFAULT_BYTE_ORDER,
    ENUM_DIR,
    HEADER_LENGTH,
    SPEC_DIR,
)
from .version import version

if sys.version_info < (3, 11):
    from backports.strenum import StrEnum
else:
    from enum import StrEnum


logger = logging.getLogger(__name__)

ENUM_NAME_SUFFIX = "__name"
DATASET_PREFIX = "AI"
DEFAULT_NAME_ENUMS = True


class EoFBehavior(StrEnum):
    IGNORE = "ignore"
    WARN = "warn"
    ERROR = "error"

    @classmethod
    def default(cls):
        return cls.ERROR


def read_value(
    buffer: bytes,
    dtype: np.dtype,
    offset: int = 0,
    shape: tp.Optional[tuple[int, ...]] = None,
    eof=EoFBehavior.ERROR,
):
    # assume no reshaping required (singleton or 1D)
    reshape = None

    if not shape:
        # read a single value
        count = 1
    else:
        if np.isscalar(shape):
            count = shape
        elif len(shape) == 1:
            count = shape[0]
        else:
            # output is >1D
            reshape = tuple(shape)
            count = np.prod(reshape)

    data = np.frombuffer(buffer, dtype, count, offset=offset)
    if len(data) < count:
        if eof == EoFBehavior.ERROR:
            raise RuntimeError(f"Could not read {count} items from byte {offset}")
        elif eof == EoFBehavior.WARN:
            logger.warning("Could not read %s items from byte %s", count, offset)

        # if not error, pad right with 0s
        data = np.pad(data, [(0, count - len(data))])

    if not shape:
        # want singleton
        return data[0]

    if reshape is None:
        # wanted 1D array
        return data

    return data.reshape(reshape, order=DEFAULT_AXIS_ORDER)


class EnumMapping:
    def __init__(self, values_names: list[tuple[int, str]]) -> None:
        self._value_to_name = dict()
        self._name_to_value = dict()
        for v, n in values_names:
            self._value_to_name[v] = n
            self._name_to_value[n] = v

        if len(self._value_to_name) != len(self._name_to_value):
            raise ValueError("Bidirectional mappings must have same length")

    def get_value(self, name: str) -> int:
        return self._name_to_value[name]

    def get_name(self, value: int) -> str:
        return self._value_to_name[value]

    @classmethod
    def from_tsv(cls, fpath: Path):
        out = []
        with open(fpath) as f:
            for line in f:
                val_str, name = line.split("\t")
                out.append((int(val_str), name.strip()))
        return cls(out)


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

    def read_into(self, f, out=None, force=False, name_enums=DEFAULT_NAME_ENUMS):
        if out is None:
            out = dict()

        if self.name in out and not force:
            return out

        val = read_value(f, self.dtype, self.offset, self.realise_shape(out))
        out[self.name] = val

        if name_enums and self.name in ENUMS:
            name = ENUMS[self.name].get_name(val)
            out[self.name + ENUM_NAME_SUFFIX] = name

        return out

    @classmethod
    def dtype_to_jso(cls, value):
        """Convert numpy value to something JSONable"""
        val = value.tolist()
        if isinstance(val, bytes):
            val = val.decode()
        return val

    def jso_to_dtype(self, value):
        """Convert something JSONable to its numpy equivalent according to spec"""
        if isinstance(value, str):
            value = value.encode()
        arr = np.asarray(value, self.dtype)
        if isinstance(value, list):
            return arr
        return arr.reshape(1)[0]


ENUMS: dict[str, EnumMapping] = {
    p.stem: EnumMapping.from_tsv(p) for p in ENUM_DIR.glob("*.tsv")
}


SPECS: dict[int, tuple[SpecTuple, ...]] = {
    int(tsv.stem[1:]): tuple(SpecTuple.from_file(tsv)) for tsv in SPEC_DIR.glob("*.tsv")
}


def _parse_with_version(b: bytes, version: int, name_enums=DEFAULT_NAME_ENUMS):
    spec = SPECS[version]
    out = dict()
    for line in spec:
        line.read_into(b, out, name_enums=name_enums)
    return out


def parse_bytes(b: bytes, name_enums=DEFAULT_NAME_ENUMS):
    d = _parse_with_version(b, 0, name_enums=name_enums)
    return _parse_with_version(b, d["FileVersion"], name_enums=name_enums)


def parse_file(fpath: Path, name_enums=DEFAULT_NAME_ENUMS):
    with open(fpath, "rb") as f:
        b = f.read(HEADER_LENGTH)
        return parse_bytes(b, name_enums=name_enums)


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
    def from_bytes(
        cls, b: bytes, name_enums=DEFAULT_NAME_ENUMS, eof=EoFBehavior.default()
    ):
        meta = parse_bytes(b, name_enums=name_enums)
        header = b[:HEADER_LENGTH]
        shape = (meta["ChanNum"], meta["XResolution"], meta["YResolution"])
        dtype = np.dtype("u1" if meta["EightBit"] else ">i2")
        data = read_value(b, dtype, HEADER_LENGTH, shape, eof)

        footer_starts = int(HEADER_LENGTH + data.nbytes)
        if footer_starts >= len(b):
            footer = None
        else:
            footer = b[footer_starts:]

        return cls(meta, data, header, footer)

    @classmethod
    def from_file(
        cls, fpath: Path, name_enums=DEFAULT_NAME_ENUMS, eof=EoFBehavior.default()
    ):
        with open(fpath, "rb") as f:
            return cls.from_bytes(f.read(), name_enums=name_enums, eof=eof)

    def header_hex(self) -> tp.Optional[str]:
        if self.header is None:
            return None
        return self.header.hex()

    def footer_hex(self) -> tp.Optional[str]:
        if self.footer is None:
            return None
        return self.footer.hex()


def metadata_to_jso(meta: dict[str, tp.Any]) -> dict[str, tp.Any]:
    file_ver = meta["FileVersion"]
    spec = SPECS[file_ver]
    out = dict()
    for item in spec:
        out[item.name] = item.dtype_to_jso(meta[item.name])
    return out


def metadata_to_numpy(meta: dict[str, tp.Any]) -> dict[str, tp.Any]:
    file_ver = meta["FileVersion"]
    spec = SPECS[file_ver]
    out = dict()
    for item in spec:
        out[item.name] = item.jso_to_dtype(meta[item.name])
    return out


def split_channels(
    dat_path: Path,
    json_metadata=False,
    name_enums=DEFAULT_NAME_ENUMS,
    eof=EoFBehavior.default(),
) -> tuple[dict[str, tp.Any], list[str], np.ndarray]:
    all_data = ParsedData.from_file(dat_path, name_enums=name_enums, eof=eof)
    channel_names = []
    for input_id in range(1, 5):
        ds = f"{DATASET_PREFIX}{input_id}"

        if all_data.meta[ds]:
            channel_names.append(ds)

    if json_metadata:
        meta = metadata_to_jso(all_data.meta)
        if all_data.header is not None:
            meta["_header"] = all_data.header.hex()
        if all_data.footer is not None:
            meta["_footer"] = all_data.footer.hex()
    else:
        meta = all_data.meta
        if all_data.header is not None:
            meta["_header"] = np.frombuffer(all_data.header, "uint8")
        if all_data.footer is not None:
            meta["_footer"] = np.frombuffer(all_data.footer, "uint8")

    meta["_dat2hdf5_version"] = version
    return meta, channel_names, all_data.data


def get_bytes(d: dict[str, tp.Any], key: str):
    val = d.get(key)
    if val is None:
        return b""

    if isinstance(val, str):
        return bytes.fromhex(val)
    elif isinstance(val, np.ndarray):
        return val.tobytes()
    raise ValueError(
        "Expected str (hex-encoded) or numpy array "
        f"to convert into bytes, got {type(val)}"
    )


def md5sum(b):
    md5 = hashlib.md5()
    md5.update(b)
    return md5.hexdigest()


def group_to_bytes(g, json_metadata=False, check_header=True):
    if json_metadata:
        meta = metadata_to_numpy(g.attrs)
    else:
        meta = g.attrs

    header = write_header(meta)
    if check_header:
        stored_header = get_bytes(meta, "_header")
        if stored_header and md5sum(stored_header) != md5sum(header):
            raise RuntimeError(
                f"Stored header (length {len(stored_header)}) is different to "
                f"calculated header (length {len(header)})"
            )
    footer = get_bytes(meta, "_footer")

    to_stack = []
    for input_id in range(1, 5):
        ds_name = f"{DATASET_PREFIX}{input_id}"
        if ds_name not in g:
            continue
        to_stack.append(g[ds_name][:])

    stacked = np.stack(to_stack, axis=0)
    dtype = stacked.dtype.newbyteorder(DEFAULT_BYTE_ORDER)
    b = np.asarray(stacked, dtype, order="F").tobytes(order="F")
    return header + b + footer
