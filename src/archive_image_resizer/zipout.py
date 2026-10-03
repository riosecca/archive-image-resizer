import shutil
import time
import zipfile
from pathlib import Path


def _zipinfo(src: Path, arcname, compress_type):
    """ZipInfo from src's mtime and mode. ZIP cannot store years before 1980 (or after 2107), so clamp."""
    st = src.stat()
    t = time.localtime(st.st_mtime)[:6]
    if t[0] < 1980:
        t = (1980, 1, 1, 0, 0, 0)
    elif t[0] > 2107:
        t = (2107, 12, 31, 23, 59, 58)
    zi = zipfile.ZipInfo(arcname, date_time=t)
    zi.compress_type = compress_type
    zi.external_attr = (st.st_mode & 0xFFFF) << 16
    return zi


class ZipOut:
    """A single ZIP by default. With volume_size, split into independent ZIPs: out_001.zip, out_002.zip, ...

    Note: --resume is not supported with split output (in_zip covers only the current volume).
    Splitting is off by default.
    """

    def __init__(self, path, volume_size=None):
        self.base = Path(path)
        self.volume_size = volume_size
        self.base.parent.mkdir(parents=True, exist_ok=True)
        self.idx = 1
        self.zf = None
        self._open()

    def _current_path(self):
        if not self.volume_size:
            return self.base
        return self.base.with_name(f"{self.base.stem}_{self.idx:03d}{self.base.suffix}")

    def _open(self):
        self.zf = zipfile.ZipFile(self._current_path(), "a", zipfile.ZIP_STORED)

    def add(self, src: Path, arcname: str, compress=False, data: bytes = None):
        size = len(data) if data is not None else src.stat().st_size
        if self.volume_size and self._current_path().exists():
            if self._current_path().stat().st_size + size > self.volume_size and self.zf.namelist():
                self.zf.close()
                self.idx += 1
                self._open()
        ct = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
        zi = _zipinfo(src, arcname, ct)
        if data is not None:
            self.zf.writestr(zi, data)
        else:
            with open(src, "rb") as f, self.zf.open(zi, "w", force_zip64=size >= zipfile.ZIP64_LIMIT) as w:
                shutil.copyfileobj(f, w, 1024 * 1024)
        self.zf.fp.flush()

    def names(self):
        return set(self.zf.namelist())

    def close(self):
        self.zf.close()
