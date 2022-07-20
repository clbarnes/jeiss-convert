import json

from jeiss_convert.meta import main as datmeta

# todo: add this to jeiss-specs and import from there
MAGIC_NUMBER = 3_555_587_570


def get_output(capsys, *args: str):
    result = datmeta([str(arg) for arg in args])
    outerr = capsys.readouterr()

    return result, outerr.out, outerr.err


def test_json(dat_path, capsys):
    val, out, _ = get_output(capsys, "json", str(dat_path))
    assert val == 0
    meta = json.loads(out)
    assert isinstance(meta, dict)


def test_json_subset(dat_path, capsys):
    keys = ["FileMagicNum", "FileVersion"]
    val, out, _ = get_output(capsys, "json", dat_path, *keys)
    assert val == 0
    meta = json.loads(out)
    assert set(keys) == set(meta)


def test_fmt(dat_path, capsys):
    val, out, _ = get_output(capsys, "fmt", dat_path, "magic {FileMagicNum}")
    assert val == 0
    assert out.rstrip() == f"magic {MAGIC_NUMBER}"


def test_list(dat_path, capsys):
    val, out, _ = get_output(capsys, "list", dat_path)
    assert val == 0
    assert out.rstrip().splitlines()


def test_get(dat_path, capsys):
    val, out, _ = get_output(capsys, "get", dat_path)
    assert val == 0
    assert out.rstrip().splitlines()


def test_get_subset(dat_path, capsys):
    keys = ["FileMagicNum", "FileVersion"]
    val, out, _ = get_output(capsys, "get", dat_path, *keys)
    assert val == 0
    assert len(out.rstrip().splitlines()) == len(keys)
