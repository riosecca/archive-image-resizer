import logging
import logging.handlers
import re
import shutil
import time
from pathlib import Path

from . import archive, imaging, throttle
from .state import State
from .zipout import ZipOut


def setup_log(log_dir):
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log = logging.getLogger("shrinker")
    log.setLevel(logging.INFO)
    log.handlers.clear()
    fn = Path(log_dir) / f"process_{time.strftime('%Y%m%d')}.log"
    h = logging.handlers.RotatingFileHandler(fn, maxBytes=5_000_000, backupCount=5, encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(h)
    log.addHandler(logging.StreamHandler())
    return log


def _mb(n):
    return f"{n / 1048576:.1f}MB"


def write_progress(path, state, total, started, limit, handled):
    s = state.summary()
    n = s["done"] + s["error"]
    target = min(total, limit) if limit else total
    el = time.time() - started
    eta = (el / handled * (target - n)) if handled else 0  # estimate from this run's speed (works with --resume)
    pct = 100 * n / target if target else 100
    ratio = 100 * s["out_bytes"] / s["orig_bytes"] if s["orig_bytes"] else 0
    Path(path).write_text(
        f"Progress: {n}/{target} ({pct:.1f}%)  done {s['done']} errors {s['error']}\n"
        f"Size: {_mb(s['orig_bytes'])} -> {_mb(s['out_bytes'])} ({ratio:.0f}%)\n"
        f"Elapsed: {el / 60:.1f} min  ETA: {eta / 60:.1f} min\n"
        f"Updated: {time.strftime('%F %T')}\n",
        encoding="utf-8",
    )


def stamped_glob(output):
    o = Path(output)
    return f"{o.parent}/{o.stem}-??????-??????*{o.suffix}"


def new_output(output):
    """output/output.zip -> output/output-yymmdd-HHMMSS.zip"""
    o = Path(output)
    return o.with_name(f"{o.stem}-{time.strftime('%y%m%d-%H%M%S')}{o.suffix}")


def find_resume_output(output):
    """Resume target: the latest timestamped ZIP (split _NNN parts are grouped under the base name)."""
    o = Path(output)
    pat = re.compile(re.escape(o.stem) + r"-(\d{6}-\d{6})(_\d{3})?" + re.escape(o.suffix) + "$")
    found = sorted({m.group(1) for f in o.parent.glob("*") if (m := pat.fullmatch(f.name))})
    return o.with_name(f"{o.stem}-{found[-1]}{o.suffix}") if found else None


def alt_arcname(name, suffix):
    p = Path(name)
    return str(p.with_name(f"{p.stem} ({p.suffix.lstrip('.').lower()}){suffix}"))


def unique_arcname(name, suffix, orig_names, claimed):
    """Name inside the output ZIP. Never reuse a name taken by another source file or an earlier output.

    claimed maps arcname -> source name for outputs already written (or recorded as done).
    """
    arc = name if suffix is None else str(Path(name).with_suffix(suffix))
    if arc == name:
        return arc

    def taken(a):
        return a in orig_names or claimed.get(a, name) != name

    if not taken(arc):
        return arc
    alt = alt_arcname(name, suffix)  # e.g. X.png -> "X (png).jpg"
    cand, n = alt, 2
    while taken(cand):
        p = Path(alt)
        cand = str(p.with_name(f"{p.stem}-{n}{p.suffix}"))
        n += 1
    return cand


def run(cfg, resume=False, limit=None, dry_run=False):
    log = setup_log(cfg["log_dir"])
    throttle.lower_priority()
    work = Path(cfg["work_dir"])
    state_path = Path(cfg["state_file"])
    out_path = None
    if not dry_run:
        out_path = find_resume_output(cfg["output"]) if resume else new_output(cfg["output"])
        if out_path is None:
            log.error("No output ZIP (%s) found to resume", stamped_glob(cfg["output"]))
            return 2
        if not resume and out_path.exists():
            log.error("Output ZIP already exists: %s (wait a second and rerun)", out_path)
            return 2
    if not resume and not dry_run and state_path.exists():
        state_path.unlink()
    state = State(state_path)
    zip_enc = cfg.get("zip_name_encoding")
    entries = archive.list_files(cfg["input"], zip_enc)
    total = len(entries)
    orig_names = {e["name"] for e in entries}
    log.info("archive=%s files=%d limit=%s", cfg["input"], total, limit)
    if dry_run:
        for e in entries[: limit or total]:
            print(e["size"], e["name"])
        return 0
    zout = ZipOut(out_path, cfg["zip_volume_size"])
    log.info("output=%s", out_path)
    in_zip = zout.names()
    if not cfg["zip_volume_size"]:
        # The ZIP directory is only written on close, so a killed run can lose entries that state calls done.
        for n, v in list(state.files.items()):
            if v.get("status") == "done" and v.get("arc") and v["arc"] not in in_zip:
                log.warning("Missing from output ZIP, will redo: %s", n)
                state.forget(n)
    claimed = {v["arc"]: n for n, v in state.files.items() if v.get("status") == "done" and v.get("arc")}
    progress = Path(cfg["log_dir"]) / "progress.txt"
    started, handled = time.time(), 0
    tcfg = cfg["throttle"]
    try:
        for e in entries:
            name = e["name"]
            if state.status(name) == "done":
                continue
            if limit and handled >= limit:
                break
            throttle.wait_if_busy(tcfg, log)
            t0 = time.time()
            src = None
            try:
                src = archive.extract_one(cfg["input"], name, work / "extract", zip_enc)
                suffix, data, info = imaging.convert(src, cfg)
                arc = unique_arcname(name, suffix, orig_names, claimed)
                if arc not in in_zip:
                    if data is None:
                        zout.add(src, arc, compress=info["action"].startswith("copy") and src.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".zip", ".rar", ".mp4"))
                    else:
                        zout.add(src, arc, data=data)
                    in_zip.add(arc)
                claimed[arc] = name
                out_size = len(data) if data is not None else e["size"]
                state.set(name, status="done", arc=arc, orig_size=e["size"], out_size=out_size,
                          action=info["action"], height=info.get("height"), scale=info.get("scale"))
                log.info("OK %s %s -> %s %sx%s scale=%s q=%s %s %.2fs%s", name, _mb(e["size"]), _mb(out_size),
                         info.get("width"), info.get("height"), info.get("scale"), info.get("quality"),
                         info["action"], time.time() - t0, f" err={info['error']}" if info.get("error") else "")
            except Exception as ex:
                state.set(name, status="error", error=str(ex), orig_size=0)
                log.error("NG %s %s", name, ex)
            finally:
                if src and src.exists():
                    src.unlink()  # delete the extracted source file right away
            handled += 1
            write_progress(progress, state, total, started, limit, handled)
            time.sleep(tcfg["sleep_ms"] / 1000)
    finally:
        zout.close()
    s = state.summary()
    log.info("finished %s", s)
    if s["error"] == 0 and handled and not limit and all(state.status(e["name"]) == "done" for e in entries):
        shutil.rmtree(work / "extract", ignore_errors=True)  # remove the work area only when everything succeeded
    return 0 if s["error"] == 0 else 1
