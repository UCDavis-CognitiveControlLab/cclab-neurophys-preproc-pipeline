# CC Lab Data Organization Standard: how this repo applies it

The standard itself is in `CCLabDataOrg/CC Lab Data Organization Standard.md`. This page covers how the pipeline
maps onto it and what it adds where the standard leaves things open.

## What the pipeline enforces

| standard | in this repo |
|---|---|
| `session_id = <animal>_<YYYYMMDD>_<area>` | derived from `[session]`; never typed by hand |
| controlled vocabulary (animal, area, probe, task) | checked when a config loads (`src/cclab_preproc/config.py`) |
| `probe → animal → session → task → raw / processed / derivatives` | all relative paths resolve inside this tree |
| probe folders `neuropixel`, `plexon`, `ripple` | from probe tokens `npx`, `sprobe`, `ripple` |
| `raw/` immutable | the pipeline only reads `raw/` |
| grab-and-go `<task>.mat` | `cclab-preproc build-meta` writes `<task>/<task>.mat` |
| `sessions.csv` per probe | `Config.sessions_csv` points at `<data_root>/<probe folder>/sessions.csv` (not written automatically yet) |

## Additions (proposed; not yet in the standard)

- **Session-level `processed/`** for outputs that span task blocks: `processed/supercat/` (CatGT pass 2) and
  `processed/kilosort4/` when task blocks are sorted together. The standard only defines `processed/` inside a
  task block.
- **`processed/catgt/`** inside each task block for CatGT pass-1 output.
- **`_runs/`** inside output folders for provenance records (config copy + `run.json`).
- **Metafile `session_id`** follows the standard (`venni_20250731_SEF`). `matlab/BuildRecordingMeta.m` still builds
  `<subject>_<date>_<task>` (e.g. `Venni_040825_MGSDiffDir`) and saves `<that>_meta.mat`; the two should be
  aligned.
