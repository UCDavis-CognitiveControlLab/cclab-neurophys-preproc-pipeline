"""Step 2: run Kilosort 4 on one SpikeGLX ap.bin.

    uv run python -m cclab_preproc.sort <file.ap.bin> <results folder> [--tmax SECONDS]
    uv run python -m cclab_preproc.sort <file.ap.bin> <results folder> --gui

Without ``--gui`` the sort runs with no window (works over ssh); needs
``uv sync --extra sort``. With ``--gui`` it writes the probe file and opens the
Kilosort window on this recording instead; needs ``uv sync --extra sort-gui``.

The probe layout is read from the recording's own ap.meta by the lab's
``make_kilosort4_probe_from_meta.py``, so it cannot disagree with what was recorded.
Every recorded channel is given to Kilosort, including any that SpikeGLX marks "not
used" (the probe's reference site, channel 191 on the October 2026 recordings): they
are printed so you know which they are, and can be removed after sorting.
``--drop-flagged`` leaves them out of the sort instead.
``--tmax 300`` sorts only the first 5 minutes: a quick test of a new machine.

Copy the ap.bin to a local disk first. Sorting straight off the lab share took 13 h
for one 94-minute recording.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np

from .make_kilosort4_probe_from_meta import _saved_ap_channels, probe_from_meta, read_meta, save_probe


def flagged_unused(meta: dict) -> list[int]:
    """Columns of the .bin that SpikeGLX marks "not used" in ~snsGeomMap (the probe's reference site)."""
    if "~snsGeomMap" not in meta:
        return []
    used = np.array([int(e.split(":")[3]) for e in re.findall(r"\(([^)]*)\)", meta["~snsGeomMap"])[1:]])
    saved_ap, _ = _saved_ap_channels(meta)
    return np.flatnonzero(used[saved_ap] == 0).tolist()


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("ap_bin", type=Path)
    p.add_argument("results_dir", type=Path)
    p.add_argument("--tmax", type=float, default=float("inf"), help="sort only the first N seconds")
    p.add_argument("--gui", action="store_true", help="open the Kilosort window on this file instead of sorting")
    p.add_argument(
        "--drop-flagged",
        action="store_true",
        help="leave channels SpikeGLX marks unused (the reference site) out of the sort; default keeps them",
    )
    a = p.parse_args(argv)

    meta_path = a.ap_bin.with_suffix(".meta")
    for f in (a.ap_bin, meta_path):
        if not f.is_file():
            raise SystemExit(f"error: file not found: {f}")
    meta = read_meta(meta_path)
    flagged = flagged_unused(meta)
    drop = flagged if a.drop_flagged else []
    probe = probe_from_meta(meta_path, exclude_channels=drop)
    n_chan_bin, fs = probe.pop("_n_chan_bin"), float(meta["imSampRate"])
    print(f"recording : {a.ap_bin}")
    print(f"results   : {a.results_dir}")
    print(f"probe     : {probe['n_chan']} channels, y {probe['yc'].min():g}..{probe['yc'].max():g} um")
    print(f"flagged   : SpikeGLX marks {flagged} unused; {'dropped from' if a.drop_flagged else 'kept in'} the sort")
    print(f"settings  : n_chan_bin={n_chan_bin}  fs={fs}  tmax={a.tmax}")

    if a.gui:
        try:
            from kilosort.gui.launch import launcher
        except ImportError as e:
            raise SystemExit(f"error: the Kilosort window needs `uv sync --extra sort-gui` ({e})")
        probe_file = a.results_dir.parent / (a.ap_bin.with_suffix("").name + "_ks4_probe.json")
        probe_file.parent.mkdir(parents=True, exist_ok=True)
        save_probe(probe, probe_file)
        print(f"probe file: {probe_file}")
        print("In the window: load that probe file, enter n_chan_bin and fs from above, set the results folder.")
        launcher(str(a.ap_bin))
        return

    try:
        from kilosort import run_kilosort  # imported late: optional, heavy dependency
    except ImportError as e:
        raise SystemExit(f"error: sorting needs `uv sync --extra sort` ({e})")
    # Everything else is the Kilosort default, which is what the lab has used so far.
    settings = {"n_chan_bin": n_chan_bin, "fs": fs, "tmax": a.tmax}
    run_kilosort(settings, probe=probe, filename=a.ap_bin, results_dir=a.results_dir)


if __name__ == "__main__":
    main()
