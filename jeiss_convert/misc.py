import sys
from pathlib import Path

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib


SPEC_ROOT = Path(__file__).resolve().parent / "jeiss-specs"
SPEC_DIR = SPEC_ROOT / "specs"
ENUM_DIR = SPEC_ROOT / "enums"

with open(SPEC_ROOT / "misc.toml", "rb") as f:
    _misc = tomllib.load(f)

DEFAULT_AXIS_ORDER = _misc["array_order"]
DEFAULT_BYTE_ORDER = _misc["byte_endianness"]
HEADER_LENGTH = _misc["data_offset"]
MAGIC_NUMBER = _misc["magic_number"]
DATE_FORMAT = _misc["date"]["format"]
DATE_FIELDS = _misc["date"]["fields"]
