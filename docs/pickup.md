# Pickup notes: movie-paradigm sorting (Venni, Oct 2026)

Last updated 2026-11-18. Delete or rewrite this file once the movie sessions are sorted.

## Goal

Spike-sort the "movie" paradigm recordings from the 10/09–10/12/2026 Venni sessions with Kilosort 4.

## Where the movie data is (surveyed 2026-11-18)

NAS = `R:\shared\current\Neuropixel` (`\\cns-nas.ucdavis.edu\cclab`). Sorting PC = `cns-ddhn7qkm3`
(RTX A4000 16 GB, 32 GB RAM).

| Date | Folder | Movie behavior | Movie neural data | Status |
|---|---|---|---|---|
| 10/07 | `100726_V_SEF` | `Movie+MGS\matlab\mgsmo*.mat` only | none | nothing to sort |
| 10/09 | `100926_Venni_SEF_ACC` | `movie\2026-10-09_124846_exp\` | `movie1_g0\` on the NAS, 1 probe (NP1032), 94 min, 130 GB | **sorted** 11/04–05 (KS 4.1.7): 609 units, 267 good, drift 6.5 µm. Not curated in Phy (`cluster_group.tsv` == `cluster_KSLabel.tsv`) |
| 10/10 | `101026_V_SEF_ACC` | `Movie\2026-10-10_130828_exp\` | **missing** (on the NAS since 2026-11-20: `Movie\Movie_g0`, see [TODO.md](TODO.md)) | `MGSFV\neuro\` is empty too. Not on `D:`, `G:`, `F:` or the NAS (searched 4 levels deep). Has to be pulled from the acquisition PC and uploaded |
| 10/11 | `101126_Vennie_SEF_ACC` | none | none | no movie that day (MGSFV + MGSVD only) |
| 10/12 | `101226_Vennie_SEF_FEF` | not on the NAS | `D:\Wenqing\SortingOngoing\101226_VDual\Movie_g0\`, 2 probes (imec0, imec1), ~40 min, 52 GB each | **unsorted** (no `kilosort4\` folder, no probe file). Only on the sorting PC's local `D:`, not on the NAS |

Notes:

- `_g0` in a SpikeGLX name is the **gate index** of the raw recording (`<run>_g<gate>_t<trigger>`), not a
  "processed" marker. A run has been sorted when its `*_imecN\` folder (or a `sorted\` / `curated\` folder)
  contains `kilosort4\` with `spike_times.npy`; CatGT output is prefixed `catgt_` / `supercat_`.
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
- `R:` is not mounted in WSL, and `D:` is only reachable through the slow `/mnt/d` bridge.
- Don't sort straight off the NAS: the 10/09 movie sort (94 min of data) took 13.3 h reading from `R:`.

## Next steps

1. Pull the 10/10 movie SpikeGLX run off the acquisition PC and upload it to
   `R:\shared\current\Neuropixel\101026_V_SEF_ACC\`. Check there for the 10/12 movie behavior folder as well.
2. Set up a Windows-side Kilosort environment (none was found under the `qmryan` Windows user): uv venv with
   `kilosort==4.1.7` and CUDA PyTorch.
3. Write a small `run_kilosort` script and sort `101226_VDual\Movie_g0` imec0 then imec1 (probe file from each
   `.ap.meta`; check whether they use the same IMRO as 10/09).
4. Copy the 10/10 run to `D:` and sort it the same way.
5. Upload results (and the 10/12 `Movie_g0` raw data) to the NAS; curate 10/09, 10/10, 10/12 in Phy.

## State of this repo / WSL environment

- Uncommitted: `.gitattributes` (untracked) and line-ending-only changes to `scripts/catgt/*.bat` that it causes;
  `.direnv/` is untracked and not in `.gitignore`.
- The WSL `.venv` was rebuilt from `uv.lock` on 2026-11-18, which removed the hand-installed
  `kilosort 4.1.7` + `torch 2.11.0+cu128`. Not needed if sorting runs on Windows. To restore (wheels are in the
  uv cache):
  `uv pip install --python .venv/bin/python "kilosort==4.1.7" "torch==2.11.0+cu128" --extra-index-url https://download.pytorch.org/whl/cu128 --index-strategy unsafe-best-match`
- No `configs/local.toml` on this machine and no session configs for the October sessions yet.
- This pipeline does not run Kilosort itself (see [pipeline.md](pipeline.md), step 2), and `build-meta` only
  understands the MGS-style behavior files, not the movie runner's output.
