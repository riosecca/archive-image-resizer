import argparse
import sys

from .config import load_config
from .pipeline import run


def main(argv=None):
    p = argparse.ArgumentParser(prog="archive-image-resizer")
    p.add_argument("--config", help="config file (default: config.yaml at the project root)")
    p.add_argument("--input", help="input archive (.rar/.zip/.7z; first volume for split RAR; overrides config)")
    p.add_argument("--output", help="base name of the output ZIP (actual file: name-yymmdd-HHMMSS.zip)")
    p.add_argument("--resume", action="store_true", help="resume by appending to the latest timestamped ZIP")
    p.add_argument("--limit", type=int, help="maximum number of files to process in this run (for testing)")
    p.add_argument("--dry-run", action="store_true", help="list files only")
    a = p.parse_args(argv)
    cfg = load_config(a.config)
    if a.input:
        cfg["input"] = a.input
    if a.output:
        cfg["output"] = a.output
    return run(cfg, resume=a.resume, limit=a.limit, dry_run=a.dry_run)


if __name__ == "__main__":
    sys.exit(main())
