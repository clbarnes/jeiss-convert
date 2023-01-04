
import logging
import typing as tp

import numpy as np

from .misc import DEFAULT_AXIS_ORDER, SPEC_DIR

logger = logging.getLogger(__name__)


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


class SelfReferentialSpecException(ValueError):
    pass


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
                try:
                    s = meta[item]
                except KeyError:
                    raise SelfReferentialSpecException(
                        f"Shape of metadata item '{self.name}' depends on value of item '{item}', which is unknown."
                    )
                out.append(s)
        return tuple(out)

    def realise_nbytes(self, meta: dict[str, int]) -> int:
        shape = self.realise_shape(meta)
        size = 1 if shape is None else np.product(shape, dtype=int)
        itemsize = self.dtype.itemsize
        return size * itemsize

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

    def read_into(self, f, out=None, force=False):
        if out is None:
            out = dict()

        if self.name in out and not force:
            return out

        out[self.name] = read_value(f, self.dtype, self.offset, self.realise_shape(out))
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

    def has_dependent_shape(self):
        return self.shape is not None and any(isinstance(s, str) for s in self.shape)

    def dtype_tuple(self, meta: tp.Optional[dict[str, int]] = None):
        if meta is None:
            meta = dict()

        dtup = [self.name]
        dtup.append(self.dtype.descr[0][1])
        shape = self.realise_shape(meta)
        if shape is not None:
            dtup.append(shape)
        return tuple(dtup)


SPECS: dict[int, tuple[SpecTuple, ...]] = {
    int(tsv.stem[1:]): tuple(sorted(SpecTuple.from_file(tsv), key=lambda s: s.offset))
    for tsv in SPEC_DIR.glob("*.tsv")
}
