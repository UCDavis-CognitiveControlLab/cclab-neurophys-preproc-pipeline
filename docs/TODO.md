# TODO: getting the pipeline running on the lab machines

Written 2026-11-20. Goal: sort the exp00 movie recordings on a lab PC with an NVIDIA GPU, starting with
`101026_V_SEF_ACC/Movie/Movie_g0` (39 min, 54 GB, the smallest complete movie session). Background and what was
found in the recordings: `cclab_movie_project/docs/PREPROCESSING.md`.

## Where things stand

Committed 2026-11-23 as a first pass (may be stripped back and rebuilt step by step):

| file | what it does | tested? |
|---|---|---|
| `src/cclab_preproc/exp00_segments.py` | TTL edges in `nidq.bin` + `event_log.csv` → one labelled row per movie segment | unit test + real 10-10 data (546 segments, counts match) |
| `src/cclab_preproc/sort.py` | Kilosort 4 on one `ap.bin`, probe layout read from `ap.meta` | probe reading checked on 10-09 and 10-10; **the sort has never been run** |
| `src/cclab_preproc/exp00_psth.py` | sanity plot: firing rate around segment onset | **never run** |
| `pyproject.toml`, `uv.lock` | `uv sync --extra sort` adds Kilosort 4.1.7; PyTorch from the CUDA index on Windows/Linux | install run on macOS only |
| `configs/npx/venni_20261010_SEF.toml` | session config for 10-10 | `show` and CatGT dry run work |
| `configs/local.toml` (not tracked) | points `data_root` at `~/dev/research/data` on the Mac | |

Partial data on the Mac in `~/dev/research/data/neuropixel/venni/`: 10-10 behavior, NI file, meta files and
`segments.csv` (complete), 4.1 of 54 GB of the 10-10 `ap.bin` (incomplete, download stopped); 10-09 Kilosort spike
times, NI file and behavior (complete except the 1 kB `nidq.meta`).

## A. Can be done on the Mac (on hold)

- [ ] `docs/setup.md`: a Windows-only path for lab members and a WSL path. Cover uv, clone, `configs/local.toml`,
      `uv sync --extra sort`, NVIDIA driver, optional CatGT download, "copy the recording to a local disk first".
- [ ] Wire `sort` and the segment step into the `cclab-preproc` CLI and the session config, so the workflow is
      `show` → `sort` → `segments` → `psth` with no hand-typed paths.
- [ ] Synthetic-data tests for `sort.py` and `exp00_psth.py`, so the first run on the lab PC is not the code's
      first run.
- [ ] Vocabulary: add `ACC` and `movie`; decide how a two-area session is named (`SEF` + `ACC` on one probe).
- [ ] Update `README.md` and `docs/known-issues.md`: no sync wave on the October movie recordings, resume TTL
      (line D) not recorded, the event-code step for MGS is still missing.
- [x] Commit (this repo and `cclab_movie_project`), 2026-11-23.
- [ ] Optional: 10-09 sanity plot from the lab's existing sort (needs only the 1 kB `nidq.meta`).

## B. Must be done on the lab PC (Windows, NVIDIA GPU)

- [ ] Machine setup: `bootstrap.ps1` from `nix-config` (apps + WSL), NVIDIA driver, clone this repo,
      `uv sync --extra sort`.
- [ ] Check PyTorch sees the GPU: `uv run python -c "import torch; print(torch.cuda.is_available())"`.
- [ ] Copy a recording from the NAS to a local disk. Sorting off the NAS took 13 h for the 94-minute 10-09 file.
- [ ] 5-minute test sort: `uv run python -m cclab_preproc.sort <ap.bin> <results> --tmax 300`.
- [ ] Full sort of 10-10, then segments and the sanity plot.
- [ ] CatGT, only if we decide to use it (see below). Kilosort filters the raw file itself, which is how the lab
      sorted 10-09.
- [ ] Phy curation (later).
- [ ] 10-11 and 10-12 once their uploads finish. 10-12 has two probes (imec0 FEF, imec1 SEF); `sort.py` and
      `exp00_segments.py` assume one.

## C. Needs people

- [ ] Which 10-10 / 10-11 site block is ACC and which is SEF (0-3.8 mm vs 7.7-11.5 mm from the tip).
- [ ] Turn the SpikeGLX sync wave on before any new recording.
- [ ] What NI analog channels 0-3 carry (probably reward).
- [ ] Check the 10-07 and 10-08 movie recordings (`100726_V_SEF`, `100826_V_FEF`); not looked at yet.

## Open decisions

- **CatGT or not.** CatGT is preprocessing that runs before sorting: it joins SpikeGLX file pieces, filters,
  corrects the small per-channel sampling delay, subtracts the common signal, removes large artifacts and writes
  TTL edge times to text files. It ships for Windows and Linux only. Options: keep it as an optional step on the lab
  PC; skip it and let Kilosort filter (current lab practice for the movie sorts); or do the same steps in Python
  with SpikeInterface, which installs through uv on any OS (see [spikeinterface.md](spikeinterface.md)). Porting or forking CatGT is not planned: about 600 kB
  of C++, no licence file, and still actively changed upstream.
- **Clock alignment without a sync wave.** Currently `firstSample` + calibrated rates from the meta files. The
  drift this leaves has not been measured.
- **Where exp00-specific code lives.** `exp00_segments.py` and `exp00_psth.py` are task-specific; they could move
  to `cclab_movie_project` and leave only the general steps here.
