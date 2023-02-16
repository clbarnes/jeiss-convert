import datetime as dt
import hashlib
import logging
import sys
import typing as tp
from collections.abc import Mapping
from io import BytesIO
from pathlib import Path

import h5py
import numpy as np

from jeiss_convert.constants import (
    DAT_NBYTES_FIELD,
    FOOTER_DS,
    HEADER_DS,
    ISO_DATE_SUFFIX,
)

from .constants import DATASET_PREFIX, ENUM_NAME_SUFFIX
from .misc import (
    DATE_FIELDS,
    DATE_FORMAT,
    DEFAULT_AXIS_ORDER,
    DEFAULT_BYTE_ORDER,
    ENUM_DIR,
    HEADER_LENGTH,
    SPEC_DIR,
)

if sys.version_info < (3, 11):
    from backports.strenum import StrEnum
else:
    from enum import StrEnum


logger = logging.getLogger(__name__)

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
    fill=None,
):
    # assume no reshaping required (singleton or 1D)
    reshape = None

    count: int

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
        if fill is None:
            raise RuntimeError(
                f"Could only read {len(data)} {dtype} from byte {offset}; "
                f"expected {count}"
            )
        else:
            logger.warning(
                "Could only read %s %s from byte %s; expected %s. Padding with %s.",
                len(data),
                dtype,
                offset,
                count,
                fill,
            )
            data = np.append(data, np.full(count - len(data), fill, dtype))

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

    def realise_shape(self, meta: dict[str, int]) -> tp.Optional[tuple[int, ...]]:
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
    def from_line(cls, line: str, headers: list[str]):
        items = dict(zip(headers, line.strip().split("\t")))

        shape: list[tp.Union[str, int]] = []
        for item in items["shape"].split(","):
            item = item.strip()
            try:
                shape.append(int(item))
            except ValueError:
                shape.append(item)

        return cls(
            items["name"], np.dtype(items["dtype"]), int(items["offset"]), tuple(shape)
        )

    @classmethod
    def from_file(cls, path):
        with open(path) as f:
            headers = [s.strip() for s in next(f).split("\t")]
            for line in f:
                yield cls.from_line(line, headers)

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


def parse_datetime(b: np.ndarray, date_format=DATE_FORMAT, encoding="UTF-8"):
    s = np.asarray(b).tobytes().decode(encoding)
    return dt.datetime.strptime(s, date_format)


def handle_dates(d: dict[str, tp.Any]) -> dict[str, tp.Any]:
    to_add = dict()

    for k in DATE_FIELDS:
        v = d.get(k)
        if v is None:
            continue

        try:
            datetime = parse_datetime(v)
        except ValueError:
            continue

        to_add[k + ISO_DATE_SUFFIX] = datetime.date().isoformat()

    d.update(to_add)
    return d


def parse_bytes(b: bytes, name_enums=DEFAULT_NAME_ENUMS):
    d = _parse_with_version(b, 0, name_enums=name_enums)
    out = _parse_with_version(b, d["FileVersion"], name_enums=name_enums)
    out[DAT_NBYTES_FIELD] = np.uint64(len(b))
    if name_enums:
        out = handle_dates(out)
    return out


def parse_file(fpath: Path, name_enums=DEFAULT_NAME_ENUMS):
    with open(fpath, "rb") as f:
        b = f.read(HEADER_LENGTH)
        return parse_bytes(b, name_enums=name_enums)


def write_header(data: Mapping[str, tp.Any]):
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
    header: bytes = b""
    footer: bytes = b""

    @classmethod
    def from_bytes(
        cls,
        b: bytes,
        name_enums=DEFAULT_NAME_ENUMS,
        fill=None,
    ):
        meta = parse_bytes(b, name_enums=name_enums)
        header = b[:HEADER_LENGTH]
        shape = (meta["ChanNum"], meta["XResolution"], meta["YResolution"])
        dtype = np.dtype("u1" if meta["EightBit"] else ">i2")
        data = read_value(b, dtype, HEADER_LENGTH, shape, fill=fill)

        footer_starts = int(HEADER_LENGTH + data.nbytes)
        footer = b[footer_starts:]

        return cls(meta, data, header, footer)

    @classmethod
    def from_file(
        cls,
        fpath: Path,
        name_enums=DEFAULT_NAME_ENUMS,
        fill=None,
    ):
        with open(fpath, "rb") as f:
            return cls.from_bytes(f.read(), name_enums=name_enums, fill=fill)


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


def get_channel_names(meta):
    channel_names = []
    for input_id in range(1, 5):
        ds = f"{DATASET_PREFIX}{input_id}"

        if meta[ds]:
            channel_names.append(ds)

    return channel_names


def as_bytes(val: tp.Optional[tp.Union[np.ndarray, str, bytes]]) -> bytes:
    if val is None:
        return b""
    elif isinstance(val, bytes):
        return val
    elif isinstance(val, str):
        return bytes.fromhex(val)

    if isinstance(val, h5py.Dataset):
        val = val[:]

    if isinstance(val, np.ndarray):
        return val.tobytes()

    raise ValueError(
        "Expected str (hex-encoded) or numpy array "
        f"to convert into bytes, got {type(val)}"
    )


def get_bytes(d: dict[str, tp.Any], key: str):
    return as_bytes(d.get(key))


def md5sum(b: bytes):
    md5 = hashlib.md5()
    md5.update(b)
    return md5.hexdigest()


def group_to_bytes(g: h5py.Group, json_metadata=False, check_header=True):
    expected_len = g.attrs[DAT_NBYTES_FIELD]
    if json_metadata:
        meta = metadata_to_numpy(g.attrs)
    else:
        meta = g.attrs

    header = write_header(meta)
    if check_header:
        stored_header = as_bytes(g.get(HEADER_DS))
        if stored_header and md5sum(stored_header) != md5sum(header):
            raise RuntimeError(
                f"Stored header (length {len(stored_header)}) is different to "
                f"calculated header (length {len(header)})"
            )

    footer = as_bytes(g.get(FOOTER_DS))

    to_stack = []
    for input_id in range(1, 5):
        ds_name = f"{DATASET_PREFIX}{input_id}"
        if ds_name not in g:
            continue
        to_stack.append(g[ds_name][:])

    stacked = np.stack(to_stack, axis=0)
    dtype = stacked.dtype.newbyteorder(DEFAULT_BYTE_ORDER)
    b = np.asarray(stacked, dtype, order="F").tobytes(order="F")
    all_b = header + b + footer

    if len(all_b) > expected_len:
        logger.warning(
            "Generated bytes longer than expected, "
            "original .dat file was probably truncated."
        )
        all_b = all_b[:expected_len]

    return all_b
