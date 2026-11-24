# Design notes: agreed direction, not built yet

Written 2026-11-23. Goal: anyone in the lab clones this repo and gets from a raw SpikeGLX recording to sorted,
curated units and a first PSTH (average firing rate around an event) without installing or wiring anything else.
Nothing in this file is implemented unless it says so.

## 1. Machine settings and "conscious" commands (spec)

Machine settings are only paths: where the data lives (`data_root`) and, optionally, where CatGT is.

**Where settings come from**, first match wins:

1. `-C <file>` / `--settings <file>` on the command line
2. `configs/local.toml` (untracked; for a personal laptop or a one-off override)
3. `configs/machines/<hostname>.toml` (tracked; one per shared lab PC, hostname lower-cased, e.g.
   `cns-ddhn7qkm3.toml`)

There is no built-in default. If none of the three exists the command stops and says which hostname it looked
for and how to create the file.

**Every command that touches data**:

- prints, before doing anything: the settings file used and why (flag / local / hostname), the hostname, the
  resolved `data_root`, and the session folder;
- checks that `data_root` and every input file it needs exist and are readable, and stops with the full path of
  the first one that is not (no partial runs);
- never writes outside the session folder.

`cclab-preproc show <session>` stays the read-only "what would happen" view and uses the same checks.

**Tracked machine files are safe** as long as this repository stays private: they contain folder paths only. No
credentials go in them.

Replaces: the current single untracked `configs/local.toml` plus the `CCLAB_DATA_ROOT` / `CCLAB_CATGT`
environment variables (drop the variables; a hidden override is the opposite of the point).

## 2. Kilosort inside the repo

- `cclab-preproc sort <session>`: headless Kilosort 4 run with settings taken from the session file and the probe
  layout read from the recording's own `ap.meta`. Same code path as the Kilosort GUI.
- `cclab-preproc sort-gui <session>`: opens the Kilosort GUI on the right file, for people who prefer it.
- Installed with `uv sync --extra sort` (Kilosort 4.1.7 + PyTorch 2.11.0, CUDA 12.8 build on Windows and Linux). Lab PCs are assumed to have
  an NVIDIA driver already.
- Run from Windows PowerShell on the sorting PC, on a local copy of the data. WSL there has 15 GB of RAM and the
  94-minute 10-09 sort peaked at 19 GB.
- A first, never-run version of the headless runner is in `src/cclab_preproc/sort.py` (one `ap.bin` at a time,
  called with `python -m`, not yet a `cclab-preproc` command).

## 3. Phy through uv (deferred)

Wanted: `cclab-preproc phy <session>` opens Phy on the session's sort folder with no separate install.

Deferred because it is untested and likely to need its own environment: Phy is older, lightly maintained and pins
older versions of its dependencies, which may not coexist with Kilosort and PyTorch. Options to try, in order:

1. a `curate` extra in this project's `pyproject.toml` (works only if the dependencies resolve together);
2. `uv tool run` / `uvx` with Phy in an isolated environment, launched by our command;
3. keep Phy as a documented separate install.

The lab currently runs Phy from source checkouts (`D:\Wenqing\phy`, `D:\Wenqing\phylib` on the sorting PC), which
is worth reading before choosing.

## 4. Task adapters and one generic PSTH

Each task gets one small adapter file whose only job is to turn that task's raw signals into a common events
table: one row per event, with `event` (name), `t_s` (seconds on the recording clock), `ap_sample`, and whatever
trial labels the task has (trial, condition, target, video, ...).

- MGS adapter: event codes 4 / 1 / 8 from the NI file plus the behavior `.mat`.
- Movie (exp00) adapter: segment on/off TTLs plus `event_log.csv`. A working version is in
  `src/cclab_preproc/exp00_segments.py`; it writes its own column names, not yet the common table.

Then `cclab-preproc psth <session> --event <name> [--by <label>]` works for any task, and is the standard sanity
check after a sort.

## 5. Decisions still open (made once, for the tool)

- **Two-probe sessions** (e.g. 10-12, imec0 FEF + imec1 SEF): proposal is to list probes in the session file and
  sort each probe separately.
- **Output format**: the lab has two (`<task>.mat` from `BuildRecordingMeta.m`, and the `session_metadata/`
  folder from `npx_session_metadata`). Pick one for this tool to write.
- **CatGT**: optional step, or dropped in favour of Kilosort's own filtering / SpikeInterface.

## 6. Cleanup queued (waiting for a go)

- Rename `provenance.py` to `run_record.py`.
- Remove the two MI analysis notebooks, their test, the `[mi_classification]` config sections and the
  dependencies only they need. They remain in CCLab-BrindaRepo and in this repo's git history.
- Convert `notebooks/Build_Recording_Meta.ipynb` to a `# %%` Python file.
