# Pickup notes: movie-paradigm sorting (Venni, Oct 2026)

Surveyed 2026-11-18; data table, next steps and repo state corrected 2026-11-23. Current task list:
[TODO.md](TODO.md). Delete this file once the movie sessions are sorted.

## Pick up here (left off 2026-11-24, evening)

**Done 11-24:**

- All four movie sessions are on `D:\Quincy\data\neuropixel\venni\`; every `ap.bin` matches `fileSizeBytes`,
  0 failed.
- Kilosort install on Windows works: `uv sync --extra sort`, `torch 2.11.0+cu128`, GPU visible.
- `sort.py` ran for the first time: 10-10, `--tmax 300`, 299 units (170 good), 315,353 spikes, drift 0.3 um,
  peak 15 GB RAM / 3.3 GB GPU. Output in `...\venni_20261010_SEF\movie\processed\kilosort4_test300` (a test;
  delete once the full sort exists).
- `sort.py` now uses the lab's probe script and has `--gui` and `--keep-flagged`. The `--gui` path has not been
  run yet.
- Hands-on walkthrough of the raw data: `scratch/explore_1010_raw.py` (header, file size, memory map, trace plot).
- Traps found on the way are in [known-issues.md](known-issues.md), "Sorting PC traps".

**Next, in order:**

1. Try `sort ... --gui` once (needs `uv sync --extra sort-gui`).
2. Full 10-10 sort (rough guess: an hour), then the other sessions one after another, not in parallel (the GPU
   is already fully busy with one sort; RAM peaked at 19 GB on the 94-minute recording).
3. Walk through the sort output in `scratch/explore_1010_KS.py` (spike times, clusters, labels).
4. Task signals (`nidq`) and the segment table on our own copy:
   `uv run python -m cclab_preproc.exp00_segments <raw\Movie_g0> <...\event_log.csv> <processed\events\segments.csv>`
   (expect 546 segments, 91 trials), then `exp00_psth` (never run), then Phy.

**Open:** keep or drop channel 191 for the real sorts (default drops; the lab's 10-09 sort kept it). Which
checkout to run from on Windows (`Q:` with `UV_PROJECT_ENVIRONMENT`, or the `D:\Quincy\code` clone). Session
config driving `sort` so no paths are typed ([design.md](design.md), sections 1-2; not built).

**Elsewhere:** the `cclab_movie_project` changes (`docs/PREPROCESSING.md`, `qc_exp00.py`) are only on the Mac, not
on GitHub. WSL disk clean-up was measured but not done.

## Goal

Spike-sort the "movie" paradigm recordings from the 10/09–10/12/2026 Venni sessions with Kilosort 4.

## Where the movie data is (checked 2026-11-23)

NAS = `R:\shared\current\Neuropixel` (`\\cns-nas.ucdavis.edu\cclab`). Sorting PC = `cns-ddhn7qkm3`
(RTX A4000 16 GB, 32 GB RAM).

| Date | Folder | Movie behavior | Movie neural data | Status |
|---|---|---|---|---|
| 10/07 | `100726_V_SEF` | `Movie+MGS\matlab\mgsmo*.mat` only | none | nothing to sort |
| 10/09 | `100926_Venni_SEF_ACC` | `movie\2026-10-09_124846_exp\` | `movie1_g0\` on the NAS, 1 probe (NP1032), 94 min, 130 GB | **sorted** 11/04–05 (KS 4.1.7): 609 units, 267 good, drift 6.5 µm. Not curated in Phy (`cluster_group.tsv` == `cluster_KSLabel.tsv`) |
| 10/10 | `101026_V_SEF_ACC` | `Movie\2026-10-10_130828_exp\` | `Movie\Movie_g0\` on the NAS (uploaded 11-20), 1 probe, 39 min, 50 GB | **unsorted** |
| 10/11 | `101126_Vennie_SEF_ACC` | not in the session folder; `R:\shared\experiment_packages\runs\exp00\2026-10-11_125148_exp\` | `Movie\Movie2_g0\` on the NAS (uploaded 11-20), 1 probe, 84 min, 108 GB. `Movie\Movie_g0\` is a 6 min false start | **unsorted** |
| 10/12 | `101226_Vennie_SEF_FEF` | not in the session folder; `R:\shared\experiment_packages\runs\exp00\2026-10-12_120830_exp\` | `D:\Wenqing\SortingOngoing\101226_VDual\Movie_g0\`, 2 probes (imec0, imec1), 40 min, 52 GB each. Also on the NAS since 11-20, rearranged as `Movie\P1(FEF)\Movie_g0_imec0\` and `Movie\P2(SEF)\Movie_g0_imec1\` | **unsorted** (no `kilosort4\` folder, no probe file). Sync wave is on for this one |

Notes:

- `_g0` in a SpikeGLX name is the **gate index** of the raw recording (`<run>_g<gate>_t<trigger>`), not a
  "processed" marker. A run has been sorted when its `*_imecN\` folder (or a `sorted\` / `curated\` folder)
  contains `kilosort4\` with `spike_times.npy`; CatGT output is prefixed `catgt_` / `supercat_`.
- Every `.bin` above matches the `fileSizeBytes` in its `.meta` (checked 11-23), so the uploads are complete.
- Local working copies go under `D:\Quincy\data\` (see [data-transfer.md](data-transfer.md)).
- `G:` is an archive of 2023-2024 sessions, not a workspace; none of the October sessions are on it.
- The movie behavior folders come from the movie runner (`run_metadata.json`, `event_log.csv`,
  `segment_diagnostics.csv`, `session_plan.csv`, EyeLink `.edf`). Acquisition/behavior PC: `CNS-DD1XSH0R3`;
  `run_metadata.json` points at `Z:\shared\experiment_packages\exp00_...\cclab_movie_project`.
- Raw SpikeGLX data on the acquisition PC is probably under `C:\SGL_DATA\` (the 10/09 `.ap.meta` has
  `imroFile=C:/SGL_DATA/032526_I/firstsecond.imro`).

## "Probe config / stats" files

There is no single file. What exists:

- **Probe / channel map**: `<run>_t0.imecN.ap_ks4_probe.mat` next to the `.ap.bin` (newer sorts), or
  `<run>_t0.imecN.ap_kilosortChanMap.mat` (older sorts on `D:\Wenqing\SortingOngoing`). Both are derived from the
  `.ap.meta`, so an unsorted run has none yet; regenerate from the `.ap.meta`.
- **Sort stats**: tail of `kilosort4\kilosort4.log` (unit counts, drift, runtime, memory) and
  `cluster_KSLabel.tsv`.
- **Session summary** (`session_info.json`, `units.csv`, `trials.csv`, `session_metadata.mat/.pkl`): only
  `101226_Vennie_SEF_FEF\MGSSkipreward\session_metadata_{SEF,FEF}\` has one. None for any movie run.

## Where to run things

Develop in WSL, **run Kilosort from Windows (PowerShell)** on data copied to local `D:`:

- Windows sees the RTX A4000 and has `uv.exe`; in WSL `nvidia-smi` fails and CUDA was never confirmed.
- WSL is capped at 15 GB RAM; the 10/09 movie sort peaked at 19 GB.
- `R:` is not mounted in WSL, and `D:` is only reachable through the `/mnt/d` bridge (fine for reading small
  pieces, not for sorting).
- GPU driver 573.44 (checked 11-23).
- Don't sort straight off the NAS: the 10/09 movie sort (94 min of data) took 13.3 h reading from `R:`.

## Next steps

1. ~~Pull the 10/10 movie run off the acquisition PC and upload it.~~ Done 11-20; the 10/11 and 10/12 behavior
   folders are in `experiment_packages\runs\exp00`.
2. Set up the Windows-side Kilosort environment: from PowerShell in this repo, `uv sync --extra sort`
   (Kilosort 4.1.7 + PyTorch 2.11.0 CUDA 12.8). Not done yet.
3. Sort with `src/cclab_preproc/sort.py` (probe layout from each `.ap.meta`; written, never run). 10/12 needs
   one run per probe. Both 10/12 probes used `Vennie.imro`; 10/09 used `firstsecond.imro` and 10/10 and 10/11
   `firstthird.imro`.
4. Copy the runs to `D:\Quincy\data\` (in progress 11-23) and sort from there.
5. Upload results (and the 10/12 `Movie_g0` raw data) to the NAS; curate 10/09, 10/10, 10/12 in Phy.

## State of this repo / WSL environment

- The WSL `.venv` was rebuilt from `uv.lock` on 2026-11-18, which removed the hand-installed
  `kilosort 4.1.7` + `torch 2.11.0+cu128`. Not needed if sorting runs on Windows. To restore the same versions:
  `uv sync --extra sort` (the lockfile now pins them).
- No `configs/local.toml` on this machine. One October session config exists: `configs/npx/venni_20261010_SEF.toml`.
- Kilosort can now be run from this repo (`sort.py`, untested) but is not part of the `cclab-preproc` command
  yet, and `build-meta` only understands the MGS-style behavior files. For the movie runner's output there is
  `exp00_segments.py` (segment table from TTLs + `event_log.csv`).
