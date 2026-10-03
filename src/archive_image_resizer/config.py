from pathlib import Path

import yaml

# The only place settings are defined is config.yaml at the project root (no defaults in code)
DEFAULT_PATH = Path(__file__).resolve().parents[2] / "config.yaml"


def load_config(path=None):
    path = Path(path) if path else DEFAULT_PATH
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))
