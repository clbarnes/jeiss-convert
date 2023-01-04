import numpy as np
import typing as tp
import hashlib

from .compound import Header
from .misc import HEADER_LENGTH, DEFAULT_BYTE_ORDER
from .specs import read_value


class ParsedData(tp.NamedTuple):
    header: Header
    data: np.ndarray
    footer: tp.Optional[bytes] = None

    @classmethod
    def from_bytes(cls, b: bytes):
        meta = Header.from_bytes(b)
        shape = (meta["ChanNum"], meta["XResolution"], meta["YResolution"])
        dtype = np.dtype("u1" if meta["EightBit"] else ">i2")
        data = read_value(b, dtype, HEADER_LENGTH, shape)
        footer = b[int(HEADER_LENGTH + np.prod(shape) * dtype.itemsize) :]
        return cls(meta, data, footer)

    @classmethod
    def from_file(cls, fpath):
        with open(fpath, "rb") as f:
            return cls.from_bytes(f.read())

    def header_hex(self) -> tp.Optional[str]:
        return self.header.to_hex()

    def footer_hex(self) -> tp.Optional[str]:
        if self.footer is None:
            return None
        return self.footer.hex()

    def channel_names(self) -> list[str]:
        channel_names = []
        for input_id in range(1, 5):
            ds = f"AI{input_id}"

            if self.header[ds]:
                channel_names.append(ds)
        return channel_names



# def split_channels(
#     dat_path: Path, json_metadata=False
# ) -> tuple[dict[str, tp.Any], list[str], np.ndarray]:
#     all_data = ParsedData.from_file(dat_path)
#     channel_names = []
#     for input_id in range(1, 5):
#         ds = f"AI{input_id}"

#         if all_data.header[ds]:
#             channel_names.append(ds)

#     attr = dict()

#     if json_metadata:
#         meta = all_data.header.to_dict(is_jso=True)
#         if all_data.header is not None:
#             attr["_header"] = all_data.header.hex()
#         if all_data.footer is not None:
#             attr["_footer"] = all_data.footer.hex()
#     else:
#         meta = all_data.header
#         if all_data.header is not None:
#             meta["_header"] = np.frombuffer(all_data.header, "uint8")
#         if all_data.footer is not None:
#             meta["_footer"] = np.frombuffer(all_data.footer, "uint8")

#     meta["_dat2hdf5_version"] = version
#     return meta, channel_names, all_data.data


# def get_bytes(d: dict[str, tp.Any], key: str):
#     val = d.get(key)
#     if val is None:
#         return b""

#     if isinstance(val, str):
#         return bytes.fromhex(val)
#     elif isinstance(val, np.ndarray):
#         return val.tobytes()
#     else:
#         raise ValueError(
#             "Expected str (hex-encoded) or uint8 numpy array "
#             f"to convert into bytes, got {type(val)}"
#         )


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
        ds_name = f"AI{input_id}"
        if ds_name not in g:
            continue
        to_stack.append(g[ds_name][:])

    stacked = np.stack(to_stack, axis=0)
    dtype = stacked.dtype.newbyteorder(DEFAULT_BYTE_ORDER)
    b = np.asarray(stacked, dtype, order="F").tobytes(order="F")
    return header + b + footer
