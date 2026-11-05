# Pipeline: raw data → sorted, curated units → metafile

Run `uv run cclab-preproc show <config>` at any point: it prints the exact folder every step reads from and
writes to for that session, and flags missing inputs.

Paths below use the data-standard layout (see [data-standard.md](data-standard.md)):

```
<data_root>/neuropixel/venni/venni_20250731_SEF/      ← session folder
├── mgs/                                               ← one folder per task block
│   ├── raw/MGS1_g0/...                                SpikeGLX output, untouched
│   ├── raw/behavior/remgs1.mat                        PsychToolbox Results
│   ├── processed/catgt/catgt_MGS1_g0/                 step 1, pass 1
│   ├── processed/events/sync_event_codes.npy          synced event codes
│   └── mgs.mat                                        step 4 output
├── FV/ ...
└── processed/
    ├── supercat/supercat_MGS1_g0/                     step 1, pass 2 (all task blocks joined)
    └── kilosort4/                                     steps 2–3 (when task blocks are sorted together)
```

## 0. Before you start

- `uv sync` done, `configs/local.toml` has `data_root` and `catgt_path` (see the README).
- Raw SpikeGLX runs are copied to `<task>/raw/` and are never modified.
- Create the session config: `uv run cclab-preproc new-config`, then review it. Every option is
  explained in `configs/_template.toml` and [configuration.md](configuration.md).

## 1. CatGT: filter, clean, join (`cclab-preproc catgt`)

Replaces `scripts/catgt/pass1_for_supercat.bat` + `pass2_for_supercat.bat`. Same CatGT flags, built from the
`[catgt]` section, so you don't edit a script per session.

```bash
uv run cclab-preproc catgt configs/npx/venni_20250731_SEF.toml          # dry run: prints the commands
uv run cclab-preproc catgt configs/npx/venni_20250731_SEF.toml --run    # runs them
uv run cclab-preproc catgt configs/npx/venni_20250731_SEF.toml --run --only supercat
```

- **Pass 1**, once per task block: AP-band Butterworth filter (`apfilter`), global CAR (`gblcar`), gfix
  artifact removal (`gfix`), NI edge extraction. Output: `<task>/processed/catgt/catgt_<run>_g<gate>/`.
- **Pass 2 (supercat)**, when there are 2+ task blocks: joins the pass-1 outputs end to end so all task blocks are
  spike-sorted together and units keep the same IDs across tasks. Output:
  `<session>/processed/supercat/supercat_<firstrun>_g<gate>/`. Set `supercat = false` to sort each task block
  separately.
- CatGT's own log is copied into each output folder (`CatGT_pass1_mgs.log`, ...); the config and git commit are
  archived in `<output>/_runs/`.
- CatGT reference: <https://billkarsh.github.io/SpikeGLX/help/catgt_tshift/catgt_tshift/>

Check before moving on: the output folder has `*.ap.bin` + `*.ap.meta` (and NI edge files if `ni = true`).

## 2. Kilosort 4

Kilosort isn't installed by this repo because it needs a GPU and its own PyTorch install. Install it on the sorting
machine following <https://github.com/MouseLand/Kilosort>.

1. `uv run cclab-preproc show <config>` and copy the **Kilosort input folder** it prints.
2. In the Kilosort GUI (`python -m kilosort`), load the `*.ap.bin` from that folder and pick the probe file
   (e.g. NP1/NP2 `.json` / `.mat` channel map).
3. Set the results folder to the standard location:
   - supercat (task blocks sorted together): `<session>/processed/kilosort4/`
   - one task block: `<task>/processed/kilosort4/`
4. Note the Kilosort version and any non-default settings in the session config's `[session] notes`.

## 3. Phy curation

1. Install Phy (<https://github.com/cortex-lab/phy>), then from the Kilosort results folder run
   `phy template-gui params.py`.
2. Label clusters `good` / `mua` / `noise`, merge/split as needed, **save**. Phy writes `cluster_info.tsv` and
   `cluster_group.tsv`.
3. Update the session's row in `sessions.csv` (`sorted`, `curated`, `n_units_good`, `n_units_mua`).

## 4. Build the metafile (`cclab-preproc build-meta`)

Bundles one task block into `<task>/<task>.mat`: units + spike times (s), attempted trials aligned to the
neural clock, event codes. Same format as `matlab/BuildRecordingMeta.m`.

```bash
uv run cclab-preproc build-meta configs/npx/venni_20250731_SEF.toml
```

or open `notebooks/Build_Recording_Meta.ipynb`, which adds summaries and a PSTH sanity check per target group.

Fill in the `[meta]` section first:

| key | meaning |
|---|---|
| `task` | which task block to build |
| `ks_dir` | Kilosort/Phy results folder (relative to the task folder; `"../processed/kilosort4"` for a session-level supercat sort, but see [known-issues.md](known-issues.md#supercat-and-the-metafile)) |
| `sync_events_file` | `(N, 2)` array `[code, time_ms]` on the neural clock |
| `behavior_file` | PsychToolbox `Results` struct `.mat`; `""` skips trials |
| `label_column` | `"KSLabel"` (Kilosort's label, as in the MATLAB builder) or `"group"` (your Phy labels) |
| `inclusion` | which labels to keep, default `["good", "mua"]` |
| `code_start`, `code_attempt` | event codes for trial start (4) and trial attempt (1) |

The build stops with an error if the number of attempted behavioral trials doesn't match the number of
attempt events, because then trials and spikes would be misaligned.

MATLAB users: `matlab/BuildRecordingMeta.m` does the same thing from its CONFIG block. Behavioral files saved as
a MATLAB `table` can only be read by the MATLAB version.

## Ripple and Plexon S-Probe

The config, folder layout and metafile apply to all rigs (`probe = "ripple"` / `"sprobe"`). The CatGT step is
SpikeGLX/Neuropixels only. Ripple acquisition import (`RippleDAQ.m`, `getRipple_MGS.m` in CCLab-BrindaRepo) hasn't
been brought into this repo yet.
