# SpikeInterface: a possible replacement for the CatGT step

Written 2026-11-20 as a note for an open decision (see [TODO.md](TODO.md)). **Nothing here has been installed or
run in this repo.** The function names below are from memory of the SpikeInterface documentation; check them
against the current docs before relying on them.

- Docs: <https://spikeinterface.readthedocs.io>
- Code: <https://github.com/SpikeInterface/spikeinterface>
- Their Neuropixels walkthrough is the "Analyze Neuropixels datasets" how-to in the docs.

## What it is

A Python library for extracellular recordings. It reads raw files from most acquisition systems (including
SpikeGLX), cleans them up, runs spike sorters, and computes quality measures afterwards. It is a plain Python
package, so it installs with uv on Windows, Linux and macOS (`uv add spikeinterface`).

## Why it is relevant here

CatGT (the lab's current preprocessing tool) is a Windows/Linux program that uv cannot install. SpikeInterface
covers the same steps in Python:

| CatGT step | what it does | SpikeInterface equivalent |
|---|---|---|
| read SpikeGLX files | open `ap.bin` + `ap.meta` | `spikeinterface.extractors.read_spikeglx(folder, stream_id="imec0.ap")` (probe layout comes from the meta file) |
| `-apfilter` | keep the spike band, 300 Hz and up | `spikeinterface.preprocessing.highpass_filter` / `bandpass_filter` |
| tshift | undo the few-microsecond sampling delay between channel groups | `spikeinterface.preprocessing.phase_shift` |
| `-gblcar` | subtract the signal shared by all channels | `spikeinterface.preprocessing.common_reference` |
| `-gfix` | blank large shared artifacts | no exact match; nearest are `detect_bad_channels`, `highpass_spatial_filter`, `remove_artifacts` |
| supercat | join task blocks so units keep one identity | `spikeinterface.concatenate_recordings` |
| edge extraction (`-xd`) | TTL pulse times from the NI file | not its job; this repo's `exp00_segments.py` reads the NI file directly |

It can also start Kilosort 4 itself (`spikeinterface.sorters.run_sorter("kilosort4", recording, ...)`), export
results for Phy (`spikeinterface.exporters.export_to_phy`), and compute unit quality metrics.

## Trade-offs

- **For:** one install method on every machine; preprocessing settings live in Python next to the session config
  instead of in `.bat` files; widely used, open licence, actively maintained.
- **Against:** the lab's existing sorts used CatGT (older sessions) or raw files straight into Kilosort (the
  October movie sorts), so results would not be exactly comparable without a side-by-side check; it is a large
  dependency; one more layer to understand between the raw file and the sorter.
- **Not needed for a first sort.** Kilosort 4 filters and removes shared noise itself. SpikeInterface or CatGT
  only matters when we want the timing fix, artifact removal, or to sort several task blocks together.

## If we try it

1. Sort the same 5-minute slice three ways: raw file → Kilosort, CatGT → Kilosort, SpikeInterface → Kilosort.
2. Compare unit counts and the sanity plot before choosing one.
