"""Dispatch input archives (RAR / ZIP / 7z) by extension and expose listing and single-file extraction."""
from pathlib import Path

from . import rar

SUPPORTED = (".rar", ".zip", ".7z")


def kind(archive):
    ext = Path(archive).suffix.lower()
    if ext not in SUPPORTED:
        raise ValueError(f"Unsupported format: {archive} (supported: {', '.join(SUPPORTED)})")
    return ext[1:]


def list_files(archive, zip_name_encoding=None):
    """[{"name", "size"}] (directories excluded). zip_name_encoding: see _zip_name."""
    k = kind(archive)
    if k == "zip":
        return _zip_list(archive, zip_name_encoding)
    return _BACKENDS[k][0](archive)


def extract_one(archive, name, dest: Path, zip_name_encoding=None):
    """Extract name under dest and return its path."""
    k = kind(archive)
    if k == "zip":
        return _zip_extract(archive, name, dest, zip_name_encoding)
    return _BACKENDS[k][1](archive, name, dest)


def _safe_target(dest: Path, name):
    dest.mkdir(parents=True, exist_ok=True)
    out = (dest / name).resolve()
    if not out.is_relative_to(dest.resolve()):
        raise RuntimeError(f"Refusing unsafe path: {name}")
    return out


def _zip_name(info, encoding):
    """Names without the UTF-8 flag are read as cp437; re-decode them with `encoding` (None keeps cp437)."""
    if info.flag_bits & 0x800 or not encoding:
        return info.filename
    try:
        return info.filename.encode("cp437").decode(encoding)
    except (UnicodeEncodeError, UnicodeDecodeError):
        return info.filename


def _zip_list(archive, encoding):
    import zipfile

    with zipfile.ZipFile(archive) as z:
        return [{"name": _zip_name(i, encoding), "size": i.file_size} for i in z.infolist() if not i.is_dir()]


def _zip_extract(archive, name, dest, encoding):
    import shutil
    import zipfile

    with zipfile.ZipFile(archive) as z:
        for i in z.infolist():
            if not i.is_dir() and _zip_name(i, encoding) == name:
                out = _safe_target(dest, name)
                out.parent.mkdir(parents=True, exist_ok=True)
                with z.open(i) as src, open(out, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                return out
    raise RuntimeError(f"Not found in zip: {name}")


def _7z_list(archive):
    import py7zr

    with py7zr.SevenZipFile(archive) as z:
        return [{"name": i.filename, "size": i.uncompressed} for i in z.list() if not i.is_directory]


def _7z_extract(archive, name, dest):
    import py7zr

    out = _safe_target(dest, name)
    with py7zr.SevenZipFile(archive) as z:
        z.extract(path=dest, targets=[name])
    if not out.exists():
        raise RuntimeError(f"7z extract failed: {name}")
    return out


_BACKENDS = {
    "rar": (rar.list_files, rar.extract_one),
    "7z": (_7z_list, _7z_extract),
}
