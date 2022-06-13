#!/usr/bin/env python3
import logging
import sys
from argparse import ArgumentParser
from collections import defaultdict
from difflib import unified_diff
from pathlib import Path

logger = logging.getLogger("tsvfmt")


def fmt_lines(orig_lines, fname=None):
    out_lines = []
    for line in orig_lines:
        out_lines.append(
            "\t".join(s.strip() for s in line.strip().split("\t")) + "\n"
        )
    while out_lines[-1] == "\n":
        out_lines.pop()
    prefix = "" if not fname else "fname:"
    diff = list(
        unified_diff(
            orig_lines, out_lines, prefix + "original", prefix + "formatted"
        )
    )
    return out_lines, diff


def fmt_tsv(fpath: Path, write=False):
    orig_lines = fpath.read_text().splitlines(keepends=True)
    out_lines, diff = fmt_lines(orig_lines, str(fpath))

    if write:
        fpath.write_text("".join(out_lines))

    return diff


def fmt_stdin(write=False):
    orig_lines = sys.stdin.readlines()
    out_lines, diff = fmt_lines(orig_lines, "-")

    if write:
        sys.stdout.writelines(out_lines)

    return diff


def expand_args(args):
    out_args = defaultdict(lambda: 0)
    for arg in args:
        if arg == "-":
            args.append(None)
            continue
        p = Path(arg)
        if not p.exists():
            raise FileNotFoundError(f"Path not found: {p}")
        elif p.is_file():
            out_args[p] += 1
        elif p.is_dir():
            for p2 in p.glob("**/*.tsv"):
                out_args[p2] += 1
    return list(out_args)


def main(args=None):
    parser = ArgumentParser()
    parser.add_argument(
        "path",
        nargs="*",
        help=(
            "Path to a TSV file, "
            "directory (will be searched recursively), "
            "or - for stdin"
        ),
    )

    parser.add_argument(
        "-c",
        "--check",
        action="store_true",
        help=(
            "Do not write out changes, "
            "but error if any changes would be made"
        ),
    )
    parsed = parser.parse_args(args)

    sys.exit(_main(parsed.path, parsed.check))


def _main(paths, check):
    all_paths = expand_args(paths)
    if not all_paths:
        logger.info("No paths given, nothing to do")
        return 0

    diffs = []
    for path in all_paths:
        if path is None:
            diff = fmt_stdin(not check)
        else:
            diff = fmt_tsv(path, not check)
        if diff:
            logger.info("Format %s", path)
        diffs.extend(diff)

    if check and diffs:
        logger.warning("File(s) not formatted")
        return 1

    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
