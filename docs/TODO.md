# TODO: getting the pipeline running on the lab machines

Written 2026-11-20, corrected 2026-11-23 on the sorting PC (`cns-ddhn7qkm3`). Goal: sort the exp00 movie
recordings with Kilosort 4, starting with `101026_V_SEF_ACC/Movie/Movie_g0` (39 min, 50 GB, the smallest complete
movie session). Where the tool is heading: [design.md](design.md). Copying data: [data-transfer.md](data-transfer.md).

## Where things stand

Committed 2026-11-23 as a first pass (may be stripped back and rebuilt step by step):

| file | what it does | tested? |
|---|---|---|
| `src/cclab_preproc/exp00_segments.py` | TTL edges in `nidq.bin` + `event_log.csv` → one labelled row per movie segment | unit test + real 10-10 data on the Mac (546 segments, counts match) |
| `src/cclab_preproc/sort.py` | Kilosort 4 on one `ap.bin`, probe layout read from `ap.meta` | probe reading checked on 10-09 and 10-10; **the sort has never been run** |
| `src/cclab_preproc/exp00_psth.py` | sanity plot: firing rate around segment onset | **never run** |
| `pyproject.toml`, `uv.lock` | `uv sync --extra sort` adds Kilosort 4.1.7; on Windows/Linux PyTorch 2.11.0 from the CUDA 12.8 index | resolves; **not installed or run on Windows through this repo** |
| `configs/npx/venni_20261010_SEF.toml` | session config for 10-10 | `show` and CatGT dry run work |

Machine facts (2026-11-23): GPU is an RTX A4000 (16 GB), driver 573.44. Sorting must run from Windows PowerShell,
not WSL (WSL has 15 GB RAM; the 10-09 sort peaked at 19 GB). There is no `configs/local.toml` on this PC yet.

Data: all four movie recordings are complete on the NAS (every `.bin` matches the size in its `.meta`). Local
copies are being made under `D:\Quincy\data\neuropixel\venni\` (started 2026-11-23, about 390 GB, overnight).

The matching changes in `cclab_movie_project` (`docs/PREPROCESSING.md`, `qc_exp00.py`) are **not on GitHub yet**;
they exist only on the Mac.

## A. Code and docs

- [ ] `docs/setup.md`: a Windows-only path for lab members and a WSL path. Cover uv, clone, machine settings,
      `uv sync --extra sort`, optional CatGT download, "copy the recording to a local disk first".
- [ ] Machine settings and "conscious" commands as specified in [design.md](design.md), section 1.
- [ ] Wire `sort` and the segment step into the `cclab-preproc` CLI and the session config, so the workflow is
      `show` → `sort` → `segments` → `psth` with no hand-typed paths.
- [ ] Synthetic-data tests for `sort.py` and `exp00_psth.py`, so the first real run is not the code's first run.
- [ ] Vocabulary: add `ACC` and `movie`; decide how a two-area session is named.
- [ ] `docs/known-issues.md` still lacks: the event-code step for MGS is missing from this repo.
- [ ] Cleanup queued in [design.md](design.md), section 6 (rename to `run_record`, remove the MI notebooks,
      convert the remaining notebook).
- [ ] Phy through uv (deferred; [design.md](design.md), section 3).
- [ ] Merge [pickup.md](pickup.md) into this file, design.md and data-transfer.md. The docs overlap; facts were
      corrected in place on 2026-11-23 but not consolidated.
- [ ] Push the `cclab_movie_project` changes from the Mac (`docs/PREPROCESSING.md`, `qc_exp00.py`).
- [ ] Re-run `exp00_segments.py` on the `D:\Quincy` copy of 10-10 (so far only run on the Mac copy).

## B. On the sorting PC

- [x] Machine setup: WSL + nix, uv, repo cloned. NVIDIA driver present.
- [ ] Finish the local copies and check them ([data-transfer.md](data-transfer.md)).
- [ ] From PowerShell: `uv sync --extra sort`, then check PyTorch sees the GPU:
      `uv run python -c "import torch; print(torch.cuda.is_available())"`.
- [ ] 5-minute test sort: `uv run python -m cclab_preproc.sort <ap.bin> <results> --tmax 300`.
- [ ] Full sort of 10-10, then segments and the sanity plot.
- [ ] 10-11 (`Movie2_g0`) and 10-09 (already sorted by the lab on 11-04; re-sort only if wanted).
- [ ] 10-12: two probes (imec0 FEF, imec1 SEF). `sort.py` takes one `ap.bin` at a time, so run it once per
      probe; `exp00_segments.py` reads only `imec0`.
- [ ] CatGT, only if we decide to use it (see below).
- [ ] Phy curation (later).

## C. Needs people

- [ ] Which 10-10 / 10-11 site block is ACC and which is SEF (0-3.8 mm vs 7.7-11.5 mm from the tip).
- [ ] The SpikeGLX sync wave was off for the 10-09, 10-10 and 10-11 movie recordings and **on for 10-12**. Keep
      it on for any new recording.
- [ ] What NI analog channels 0-3 carry (probably reward).
- [ ] NAS reads from the sorting PC top out near 11 MB/s although the PC links at 1 Gbps; ask IT.
- [ ] 10-07 (`100726_V_SEF`): the 11-18 survey found movie behavior but no neural recording. 10-08
      (`100826_V_FEF`) has not been looked at.

## Open decisions

- **CatGT or not.** CatGT is preprocessing that runs before sorting: it joins SpikeGLX file pieces, filters,
  corrects the small per-channel sampling delay, subtracts the common signal, removes large artifacts and writes
  TTL edge times to text files. It ships for Windows and Linux only. Options: keep it as an optional step; skip it
  and let Kilosort filter (current lab practice for the movie sorts); or do the same steps in Python with
  SpikeInterface, which installs through uv on any OS (see [spikeinterface.md](spikeinterface.md)). Porting or
  forking CatGT is not planned: about 600 kB of C++, no licence file, and still actively changed upstream.
- **Clock alignment without a sync wave** (10-09 to 10-11). Currently `firstSample` + calibrated rates from the
  meta files. The drift this leaves has not been measured. 10-12 has the sync wave and can use it.
- **Two-probe sessions, output format**: see [design.md](design.md), section 5.
- **Where exp00-specific code lives.** `exp00_segments.py` and `exp00_psth.py` are task-specific; they could move
  to `cclab_movie_project` and leave only the general steps here.
