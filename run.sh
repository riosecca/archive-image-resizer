#!/usr/bin/env bash
# Usage: ./run.sh [options...]
#   ./run.sh --dry-run                 list only
#   ./run.sh --limit 10 --output output/test.zip
#   ./run.sh                         everything (creates output/output-yymmdd-HHMMSS.zip)
#   ./run.sh --resume                  resume after an interruption
# Without --input, uses *.part1.rar in input/ (otherwise the first *.rar / *.zip / *.7z).
set -euo pipefail
cd "$(dirname "$0")"

args=("$@")
if [[ " ${args[*]} " != *" --input "* ]]; then
  first=$(ls input/*.part1.rar input/*.part01.rar 2>/dev/null | head -n1 || true)
  [[ -z "$first" ]] && first=$(ls input/*.rar input/*.zip input/*.7z 2>/dev/null | head -n1 || true)
  [[ -z "$first" ]] && { echo "No RAR/ZIP/7z found in input/" >&2; exit 1; }
  args+=(--input "$first")
fi

exec .venv/bin/archive-image-resizer "${args[@]}"
