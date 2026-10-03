import json
import os
from pathlib import Path


class State:
    def __init__(self, path):
        self.path = Path(path)
        self.files = {}
        if self.path.exists():
            self.files = json.loads(self.path.read_text(encoding="utf-8")).get("files", {})

    def status(self, name):
        return self.files.get(name, {}).get("status")

    def set(self, name, **kw):
        self.files[name] = kw
        self.save()

    def forget(self, name):
        self.files.pop(name, None)
        self.save()

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"files": self.files}, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, self.path)  # atomic

    def summary(self):
        done = [v for v in self.files.values() if v.get("status") == "done"]
        return {
            "done": len(done),
            "error": sum(1 for v in self.files.values() if v.get("status") == "error"),
            "orig_bytes": sum(v.get("orig_size", 0) for v in done),
            "out_bytes": sum(v.get("out_size", 0) for v in done),
        }
