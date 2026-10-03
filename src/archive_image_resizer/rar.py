import logging
import re
import subprocess
from pathlib import Path


_LIST_PROBLEM = re.compile(r"is not RAR archive|Cannot open|Unexpected end of archive|Corrupt header", re.I)


def volumes(archive):
    """Return all volumes by partN sequence from the first volume (a single file if the name is not *.partN.rar)."""
    m = re.match(r"(.*\.part)(\d+)(\.rar)$", str(archive), re.I)
    if not m:
        return [Path(archive)]
    pre, num, suf = m.groups()
    out, n = [], int(num)
    while Path(f"{pre}{n:0{len(num)}d}{suf}").exists():
        out.append(Path(f"{pre}{n:0{len(num)}d}{suf}"))
        n += 1
    return out


def list_files(archive):
    """List every volume in order, dropping duplicates for files that span volumes."""
    seen, entries = set(), []
    for vol in volumes(archive):
        for e in _list_volume(vol):
            if e["name"] not in seen:
                seen.add(e["name"])
                entries.append(e)
    return entries


def _list_volume(archive):
    """Parse `unrar lt` and return the name and size of each file (directories excluded)."""
    r = subprocess.run(["unrar", "lt", str(archive)], capture_output=True, text=True, errors="replace")
    entries, cur = [], {}
    for line in r.stdout.splitlines():
        line = line.strip()
        if line.startswith("Name:"):
            cur = {"name": line[5:].strip()}
        elif line.startswith("Type:") and cur:
            cur["type"] = line[5:].strip()
        elif line.startswith("Size:") and cur:
            cur["size"] = int(line[5:].strip())
            if cur.get("type") == "File":
                entries.append(cur)
            cur = {}
    out = r.stdout + r.stderr
    if r.returncode != 0 or _LIST_PROBLEM.search(out):  # unrar can report these with rc 0
        msg = f"unrar list rc={r.returncode} for {archive}: {out[-300:]}"
        if not entries:
            raise RuntimeError(msg)
        # entries parsed but unrar complained (missing/corrupt volume): the file list may be incomplete
        logging.getLogger("shrinker").warning(msg)
    return entries


def extract_one(archive, name, dest: Path):
    if any(c in name for c in "*?"):  # unrar treats the name as a mask and could match other files
        raise RuntimeError(f"file name contains a wildcard character (* or ?), not supported: {name}")
    dest.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        ["unrar", "x", "-o+", "-y", "-idq", "--", str(archive), name, str(dest) + "/"],  # "--": name may start with "-"
        capture_output=True, text=True, errors="replace",
    )
    out = dest / name
    if r.returncode != 0 or not out.exists():
        raise RuntimeError(f"extract failed rc={r.returncode}: {(r.stdout + r.stderr)[-300:]}")
    return out
