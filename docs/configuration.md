# Configuration

There are two kinds of file:

| file | committed? | contains |
|---|---|---|
| `configs/<probe>/<session_id>.toml` | **yes** | what was recorded + settings for every step, one per session |
| `configs/local.toml` | no (gitignored) | where things are on *this* computer: `data_root`, `catgt_path` |

Keeping machine paths out of session configs means one config works on every lab computer, and it stays a
faithful record of how the session was processed.

## Session config

Create one with `uv run cclab-preproc new-config` (or copy `configs/_template.toml`, which documents every key).
Check it with `uv run cclab-preproc show <config>`.

```toml
[session]
animal = "venni"        # controlled vocabulary: venni | isaac
date = "20250731"       # YYYYMMDD (YYYY-MM-DD also accepted)
area = "SEF"            # SEF | FEF
probe = "npx"           # npx | sprobe | ripple
penetration = "4,4"
stim = false
notes = ""

[[tasks]]               # one block per task block / acquisition run
name = "mgs"            # task folder name: mgs, mgs2, mgsVarDelay, mgsDiffDir, FV, RF, "+stim" suffix
spikeglx_run = "MGS1"   # SpikeGLX run name -> raw/MGS1_g0/
gate = 0

[catgt]                 # step 1   (see _template.toml)
[meta]                  # step 4   (see pipeline.md)
[mi_classification]     # MI notebooks (see the example configs)
```

`session_id` is derived, never typed: `<animal>_<YYYYMMDD>_<area>` → `venni_20250731_SEF`. The file name should
match it.

Values outside the controlled vocabulary are rejected with an error that says how to add them (edit the sets at
the top of `src/cclab_preproc/config.py` once the lab agrees on a new value). Unknown task names only warn.

### Paths

Any key ending in `_dir`, `_file` or `_path` is a path.

- **Relative** paths are resolved inside the data-standard layout: against the step's task folder when the
  section has `task = "..."`, otherwise against the session folder:
  `ks_dir = "processed/kilosort4"` → `<data_root>/neuropixel/venni/venni_20250731_SEF/mgs/processed/kilosort4`
- **Absolute** paths (`'D:\Neuropixel_data\...'`, `/Volumes/...`) are used as written. This is for older
  sessions that haven't been moved into the standard layout; see `configs/npx/venni_20250611_SEF.toml`.
  Use single quotes for Windows paths so backslashes aren't treated as escapes.

### Analysis windows (MI notebooks)

Windows are `[start, stop)` **bin indices**, exactly as the original notebooks used them, with the ms equivalent
written next to each one. For target-aligned windows, `ms = psth_start_ms + bin * bin_ms`; for saccade-aligned
windows (`motor_bins`, `post_saccade_bins`), `ms = -sacc_pre_ms + bin * bin_ms`.

## Machine settings: `configs/local.toml`

```toml
data_root = "D:/cclab/shared/data"           # folder containing neuropixel/, plexon/, ripple/
catgt_path = "C:/SpikeGLX/CatGT-win/CatGT.exe"
```

Environment variables override it: `CCLAB_DATA_ROOT`, `CCLAB_CATGT`. Every CLI command also takes `--data-root`.

## Choosing a config in a notebook

The first code cell of each notebook:

```python
CONFIG = os.environ.get("CCLAB_CONFIG", "configs/npx/venni_20250611_SEF.toml")
```

Edit the default string, or set `CCLAB_CONFIG` before starting Jupyter. Paths are accepted relative to the
current folder or to the repo root.

## Archiving

- **Configs are versioned in git.** Commit a session's config when you process it; edit it (and commit) when
  you reprocess. The git history is the archive.
- **Every run leaves a record** in `<output folder>/_runs/<timestamp>_<step>/`: a verbatim copy of the config,
  plus `run.json` with the git commit (and whether there were uncommitted changes), package versions, user,
  machine and data root. Any output can be traced back to the exact settings and code that made it.
