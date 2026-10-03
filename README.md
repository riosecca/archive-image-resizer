# archive-image-resizer

[English](#archive-image-resizer) | [日本語](#日本語)

Shrinks the images inside RAR / ZIP / 7z archives and packs the result into a ZIP (split RAR volumes and single-file archives both work).
The scale factor is decided by the **height in pixels**. The source archive is never modified.

## Setup

```bash
sudo apt install unrar            # only needed to read RAR (multiverse). ZIP/7z are handled in pure Python (7z via the py7zr dependency)
python3 -m venv .venv
.venv/bin/pip install -e .   # installs dependencies from pyproject.toml
```

## Usage

Run `./run.sh [options]` (when `--input` is omitted, it picks `*.part1.rar` in input/, otherwise the first rar/zip/7z). Examples: `./run.sh --dry-run` / `./run.sh --limit 10 --output output/test.zip` / `./run.sh` (everything) / `./run.sh --resume`. The equivalent commands below use `.venv/bin/archive-image-resizer` (or run them after `source .venv/bin/activate`). For split RAR, give the first volume. Always try a few files with `--limit` before a full run.

```bash
# list only (input: .rar / .zip / .7z)
archive-image-resizer --input input/xxx.part1.rar --dry-run
archive-image-resizer --input input/xxx.zip --dry-run
archive-image-resizer --input input/xxx.7z --dry-run
# try only 10 files
archive-image-resizer --input input/xxx.part1.rar --output output/test.zip --limit 10
# everything / resume after an interruption
archive-image-resizer --input input/xxx.part1.rar
archive-image-resizer --input input/xxx.part1.rar --resume
```

Without `run.sh`, use Python directly (all options are the same):

```bash
# inside the virtualenv, as a module
.venv/bin/python -m archive_image_resizer --input input/xxx.zip --dry-run
# without installing the package: run from the repository root with src on the path
PYTHONPATH=src python3 -m archive_image_resizer --input input/xxx.zip --dry-run
# from Python code
python3 -c "from archive_image_resizer.cli import main; main(['--input', 'input/xxx.zip', '--limit', '10'])"
```

Each run creates a new output ZIP named `output-yymmdd-HHMMSS.zip` (e.g. `output-260925-135136.zip`). Existing ZIPs are never deleted or overwritten; remove old ones by hand. `--resume` appends to the latest timestamped ZIP. A run without `--resume` recreates state.json. For split RAR, **keep part1 to partN in the same directory** (the first volume alone cannot be extracted).

## Progress

- `logs/progress.txt`: updated per file (count, %, size reduction, estimated time left)
- `logs/process_YYYYMMDD.log`: per-file details (size, resolution, scale, quality, time, errors)
- `work/state.json`: per-file done/error record

## Layout

| Path | Contents |
|---|---|
| `src/archive_image_resizer/` | Main code (`cli` / `pipeline` / `imaging` / `archive` (format dispatch, ZIP/7z) / `rar` / `zipout` / `state` / `throttle` / `config`) |
| `config.yaml` | Scale rules, quality, throttling, etc. **The single place for settings** (no defaults in code; another file can be given with `--config`) |
| `run.sh` | Wrapper script |
| `input/` `work/` `output/` `logs/` | Input, working area (one extracted file at a time), output ZIPs, logs. Not tracked by Git |

## Limitations

- Supported inputs: `.rar` (split allowed), `.zip`, `.7z`. Split ZIP (`.z01`), split 7z (`.7z.001`) and password-protected archives are not supported.
- With solid 7z archives, every extraction re-decompresses from the start of the block, so archives with many files are slow.
- ZIP file names without the UTF-8 flag are decoded with `zip_name_encoding` in `config.yaml` (default cp932; set `null` to keep cp437).
- If any RAR volume (part1..N) is missing, files from the missing volume onward are not listed. Check the file count with `--dry-run` before a real run.
- RAR entries whose names contain `*` or `?` are reported as errors (unrar would treat them as masks).
- 16-bit grayscale images are scaled to 8 bits; float images (mode F) are copied unchanged.
- Broken images are copied unchanged and are not counted as errors. Check the log for `copy(error)` after a run.
- `--resume` is not supported with split output ZIPs (`zip_volume_size`). Parallel processing is not implemented (single worker).
- Daily logs and old output ZIPs are not deleted automatically; remove them by hand.

## Status

- Supports RAR / ZIP / 7z input. RAR was verified end to end on a large split archive; ZIP / 7z were verified with small samples.

## License

MIT License ([LICENSE](LICENSE))

---

## 日本語

RAR / ZIP / 7z の中の画像を縮小し、結果をZIPにまとめるツールです(分割RARでも、分割されていない単体ファイルでも使えます)。
縮小率は**縦(高さ)のピクセル数**で決まります。元のアーカイブは変更しません。

### セットアップ

```bash
sudo apt install unrar            # RARを読むときのみ必要 (multiverse)。ZIP/7zはPythonだけで処理します(7zは依存の py7zr を使用)
python3 -m venv .venv
.venv/bin/pip install -e .   # 依存を pyproject.toml から導入
```

### 使い方

`./run.sh [オプション]` で実行します(`--input` を省略すると、input/ の `*.part1.rar`、なければ最初の rar/zip/7z を選びます)。例: `./run.sh --dry-run` / `./run.sh --limit 10 --output output/test.zip` / `./run.sh`(全件)/ `./run.sh --resume`。以下は同等のコマンドです(`.venv/bin/archive-image-resizer`、または `source .venv/bin/activate` の後に実行)。分割RARは先頭の巻を指定します。全件を処理する前に、必ず `--limit` で少数のファイルを試してください。

```bash
# 一覧の確認のみ (入力は .rar / .zip / .7z)
archive-image-resizer --input input/xxx.part1.rar --dry-run
archive-image-resizer --input input/xxx.zip --dry-run
archive-image-resizer --input input/xxx.7z --dry-run
# 10ファイルだけ試す
archive-image-resizer --input input/xxx.part1.rar --output output/test.zip --limit 10
# 全件 / 中断後の再開
archive-image-resizer --input input/xxx.part1.rar
archive-image-resizer --input input/xxx.part1.rar --resume
```

`run.sh` を使わず、Pythonから直接実行することもできます(オプションはすべて共通です)。

```bash
# 仮想環境(.venv)の中で、モジュールとして実行
.venv/bin/python -m archive_image_resizer --input input/xxx.zip --dry-run
# パッケージをインストールせずに、リポジトリ直下から src をパスに通して実行 (依存パッケージは必要)
PYTHONPATH=src python3 -m archive_image_resizer --input input/xxx.zip --dry-run
# Pythonコードから呼び出す
python3 -c "from archive_image_resizer.cli import main; main(['--input', 'input/xxx.zip', '--limit', '10'])"
```

出力ZIPは実行ごとに `output-yymmdd-HHMMSS.zip`(例: `output-260925-135136.zip`)の名前で新規作成します。既存のZIPは削除も上書きもしないので、古いものは手動で削除してください。`--resume` は、最新の日時付きZIPに追記して再開します。`--resume` なしで実行すると、state.json を作り直します。分割RARは、**part1〜partN を同じディレクトリに置いてください**(先頭の巻だけでは展開できません)。

### 進捗の見方

- `logs/progress.txt`: 1ファイルごとに更新されます(件数・%・サイズ削減・残り時間の目安)
- `logs/process_YYYYMMDD.log`: ファイルごとの詳細(サイズ・解像度・縮小率・品質・時間・エラー)
- `work/state.json`: ファイルごとの完了/エラーの記録

### ディレクトリ構成

| パス | 内容 |
|---|---|
| `src/archive_image_resizer/` | 本体(`cli` / `pipeline` / `imaging` / `archive`(形式の振り分け・ZIP/7z) / `rar` / `zipout` / `state` / `throttle` / `config`) |
| `config.yaml` | 縮小率・品質・負荷制御などの設定。**設定の唯一の定義場所**(コード側に初期値は持ちません。`--config` で別のファイルも指定できます) |
| `run.sh` | 実行用のラッパー |
| `input/` `work/` `output/` `logs/` | 入力・作業領域(展開は1ファイル分だけ)・出力ZIP・ログ。Git管理外 |

### 制限・注意

- 入力形式は `.rar`(分割可)・`.zip`・`.7z` です。分割ZIP(`.z01`)、分割7z(`.7z.001`)、パスワード付きのアーカイブは未対応です。
- ソリッド圧縮の7zは、1ファイルを取り出すたびにブロックの先頭から展開し直すため、ファイル数が多いと遅くなります。
- UTF-8フラグのないZIPのファイル名は、`config.yaml` の `zip_name_encoding` で読みます(既定は cp932。`null` にすると cp437 のままです)。
- RARの巻(part1〜N)が1つでも欠けていると、欠けた巻以降のファイルは一覧に出ません。本番の前に、`--dry-run` でファイル数を確認してください。
- RARで名前に `*` や `?` を含むエントリは、エラーとして報告します(unrar が名前をマスクとして扱うため)。
- 16bitのグレー画像は8bitにスケールして変換します。浮動小数点の画像(mode F)は、無変換でコピーします。
- 壊れた画像は無変換でコピーされ、エラーには数えません。実行後に、ログの `copy(error)` を確認してください。
- 分割した出力ZIP(`zip_volume_size`)では `--resume` は使えません。並列処理は未実装です(単一ワーカー)。
- 日付ごとのログと古い出力ZIPは、自動では削除しません。手動で削除してください。

### 開発状況

- RAR / ZIP / 7z の入力に対応しています。RARは大容量の分割アーカイブで最後まで処理できることを確認済みです。ZIP / 7z は小さなサンプルで確認しています。

### ライセンス

MIT License ([LICENSE](LICENSE))
