"""Interrogate and dump Jeiss FIBSEM .dat metadata."""
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path
import json

from .utils import parse_bytes, metadata_to_jso, HEADER_LENGTH


min_ver = ".".join(str(i) for i in sys.version_info[:2])


def read_meta(path: Path):
    with open(path, "rb") as f:
        b = f.read(HEADER_LENGTH)
    return parse_bytes(b)


def meta_ls(args: Namespace):
    m = read_meta(args.dat)
    for key in m:
        print(key)
    return 0


def meta_fmt(args: Namespace):
    m = read_meta(args.dat)
    for fmt in args.format:
        print(fmt.format(**m))
    return 0


def meta_json(args: Namespace):
    m = read_meta(args.dat)
    m = metadata_to_jso(m)
    if args.field:
        m = {f: m[f] for f in args.field}
    kwargs = dict()
    if args.indent is not None:
        try:
            indent = int(args.indent)
        except ValueError:
            kwargs["indent"] = args.indent
        else:
            if indent < 0:
                kwargs["separators"] = (",", ":")
            else:
                kwargs["indent"] = indent
    kwargs["sort_keys"] = bool(args.sort)
    s = json.dumps(m, **kwargs)
    print(s)
    return 0


def meta_get(args: Namespace):
    m = read_meta(args.dat)
    m = metadata_to_jso(m)
    if args.field:
        m = {f: m[f] for f in args.field}
    if args.data_only:
        fmt = lambda _, v: f"{v if isinstance(v, str) else json.dumps(v)}"
    else:
        fmt = lambda k, v: f"{k}\t{v if isinstance(v, str) else json.dumps(v)}"
    for k, v in m.items():
        print(fmt(k, v))
    return 0


def main(args=None):
    parser = ArgumentParser("datmeta", description=__doc__)
    parent_parser = ArgumentParser(add_help=False)
    parent_parser.add_argument("dat", type=Path, help="Path to .dat file")

    subparsers = parser.add_subparsers(title="subcommands")

    ls_parser = subparsers.add_parser(
        "ls", parents=[parent_parser], description="List metadata field names."
    )
    ls_parser.set_defaults(func=meta_ls)

    fmt_parser = subparsers.add_parser(
        "fmt",
        parents=[parent_parser],
        description=(
            "Use python format string notation to interpolate metadata values into string. "
            "If multiple format strings are given, print each separated by newlines."
        ),
    )
    fmt_parser.add_argument(
        "format",
        nargs="*",
        help=(
            "Format string, e.g. 'Version is {FileVersion}'. "
            f"More details at https://docs.python.org/{min_ver}/library/string.html#formatstrings. "
        ),
    )
    fmt_parser.set_defaults(func=meta_fmt)

    json_parser = subparsers.add_parser(
        "json", parents=[parent_parser], description="Dump metadata as JSON."
    )
    json_parser.set_defaults(func=meta_json)
    json_parser.add_argument("-s", "--sort", action="store_true", help="Sort JSON keys")
    json_parser.add_argument(
        "-i",
        "--indent",
        type=int,
        help=(
            "Number of spaces to indent. "
            "If negative, also strip spaces between separators."
        ),
    )
    json_parser.add_argument("field", nargs="*", help="Only dump the listed fields.")

    get_parser = subparsers.add_parser(
        "get",
        parents=[parent_parser],
        description=(
            "Read metadata values. "
            "By default, a TSV with keys in the first column and values in the second "
            "(arrays JSON-serialised); "
            "key column can be omitted."
        ),
    )
    get_parser.set_defaults(func=meta_get)
    get_parser.add_argument(
        "-d", "--data-only", action="store_true", help="Do not print field names"
    )
    get_parser.add_argument("field", nargs="*", help="Only show the given fields")

    parsed = parser.parse_args(args)
    return parsed.func(parsed)


def _main(args=None):
    sys.exit(main(args))


if __name__ == "__main__":
    _main()
