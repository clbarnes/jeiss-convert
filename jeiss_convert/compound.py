import typing as tp
from pathlib import Path
from collections.abc import Mapping

import numpy as np
import h5py

from jeiss_convert.misc import DEFAULT_AXIS_ORDER, HEADER_LENGTH
from jeiss_convert.specs import SPECS, SelfReferentialSpecException, SpecTuple

COMPOUND_SPECS = dict()


def make_compound_dtype(version: int, meta=None) -> tuple[np.dtype, dict[int, int]]:
    if meta is None:
        meta = dict()

    spec = SPECS[version]
    dtuples = []
    offset = 0
    spacers = dict()
    for stuple in spec:
        if offset < stuple.offset:
            n = stuple.offset - offset
            spacers[offset] = n
            dtuples.append((f"_{offset}_{n}", "u1", (n,)))
            offset = stuple.offset
        elif offset > stuple.offset:
            raise ValueError(
                f"Metadata field '{dtuples[-1][0]}' ends at offset {offset} "
                f"but next ('{stuple.name}') starts at {stuple.offset}"
            )
        dtype_tuple = stuple.dtype_tuple(meta)
        dtuples.append(dtype_tuple)
        offset += np.dtype([dtype_tuple]).itemsize

    if offset < HEADER_LENGTH:
        n = HEADER_LENGTH - offset
        spacers[offset] = n
        dtuples.append((f"_{offset}", "u1", (n,)))

    return np.dtype(dtuples), spacers


for v in SPECS:
    try:
        COMPOUND_SPECS[v] = make_compound_dtype(v)
    except SelfReferentialSpecException:
        continue


class Header(Mapping[str, tp.Any]):
    def __init__(self, data) -> None:
        self.data = data
        self._fields: dict[str, tp.Any] = {
            k: v for k, v in data.dtype.fields.items() if not k.startswith("_")
        }

    def __getitem__(self, key: str):
        if key not in self._fields:
            raise KeyError(f"Key not found: '{key}'")
        return self.data[key]

    def __iter__(self) -> tp.Iterator[str]:
        yield from self._fields.keys()

    def __contains__(self, key: object) -> bool:
        return key in self._fields

    def __len__(self) -> int:
        return len(self._fields)

    @classmethod
    def _from_bytes_version(cls, b: bytes, version: int, meta=None):
        try:
            dtype, _ = COMPOUND_SPECS[version]
        except KeyError:
            dtype, _ = make_compound_dtype(version, meta)
        return cls(np.frombuffer(b, dtype, 1)[0])

    @classmethod
    def from_bytes(cls, b: bytes):
        mini = cls._from_bytes_version(b, 0)
        return cls._from_bytes_version(b, mini["FileVersion"], mini)

    @classmethod
    def from_readable(cls, f: tp.BinaryIO):
        return cls.from_bytes(f.read(HEADER_LENGTH))

    @classmethod
    def from_file(cls, fpath: Path):
        with open(fpath, "rb") as f:
            return cls.from_readable(f)

    def to_bytes(self) -> bytes:
        return self.data.tobytes(DEFAULT_AXIS_ORDER)

    def to_hex(self):
        return self.to_bytes().hex()

    @classmethod
    def from_hex(cls, hex: str):
        return cls.from_bytes(bytes.fromhex(hex))

    def to_dict(self, d: tp.Optional[tp.MutableMapping[str, tp.Any]] = None, is_jso=False):
        if d is None:
            d = dict()

        if is_jso:
            file_ver = self["FileVersion"]
            spec = SPECS[file_ver]
            for item in spec:
                d[item.name] = item.dtype_to_jso(self[item.name])
        else:
            d.update(self)

        return d

    @classmethod
    def from_dict(cls, d: tp.Mapping[str, tp.Any], is_jso=False):
        ver = d["FileVersion"]
        try:
            dtype, spacers = COMPOUND_SPECS[ver]
        except KeyError:
            dtype, spacers = make_compound_dtype(ver, d)

        spec: dict[int, tp.Union[int, SpecTuple]] = {s.offset: s for s in SPECS[ver]}
        values = []
        for _, stuple_or_length in sorted([*spec.items(), *spacers.items()]):
            if isinstance(stuple_or_length, int):
                val = np.zeros(stuple_or_length, ">u1")
            else:
                val = d[stuple_or_length.name]

                if is_jso:
                    val = stuple_or_length.jso_to_dtype(val)

            values.append(val)

        all_values = [tuple(values)]
        return cls(np.array(all_values, dtype)[0])

    @classmethod
    def from_hdf5(cls, ds: h5py.Dataset):
        return cls(ds[()])

    def to_hdf5(self, group: h5py.Group, name: str):
        return group.require_dataset(
            name, shape=None, dtype=None, exact=True, data=self.data
        )

    def __eq__(self, other):
        if not isinstance(other, Header):
            return NotImplemented
        return self.to_bytes() == other.to_bytes()

    def __hash__(self):
        return hash(self.to_bytes())

    # @classmethod
    # def _from_empty(cls, version: int):
    #     return cls._from_bytes_version(b"\0" * HEADER_LENGTH, version)

    # def __setitem__(self, key, value):
    #     if key not in self._fields:
    #         raise KeyError(f"Cannot assign to key '{key}'")
    #     self.data[key] = value

    # def __delitem__(self, key: str) -> None:
    #     self.data[key] = np.zeros_like(self.data[key])
