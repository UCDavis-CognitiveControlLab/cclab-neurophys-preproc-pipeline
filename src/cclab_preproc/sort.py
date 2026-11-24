"""Step 2: run Kilosort 4 on one SpikeGLX ap.bin. Needs `uv sync --extra sort`.

    uv run python -m cclab_preproc.sort <file.ap.bin> <results folder> [--tmax SECONDS]

The probe layout is read from the recording's own ap.meta (``~snsGeomMap``), so no
hand-made probe file is needed and it cannot disagree with what was recorded.
``--tmax 300`` sorts only the first 5 minutes: a quick test of a new machine.

Copy the ap.bin to a local disk first. Sorting straight off the lab share took 13 h
for one 94-minute recording.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np

from .exp00_segments import read_meta


def probe_from_meta(meta_path: Path) -> dict:
    """Kilosort probe dict from SpikeGLX ap.meta. Channels flagged unused (the reference) are left out."""
    entries = re.findall(r"\(([^)]*)\)", read_meta(meta_path)["~snsGeomMap"])[1:]
    g = np.array([[float(v) for v in e.split(":")] for e in entries])  # shank, x, y, used
    use = np.flatnonzero(g[:, 3] == 1)
    return {
        "chanMap": use.astype(np.int32),
        "xc": g[use, 1].astype(np.float32),
        "yc": g[use, 2].astype(np.float32),
        "kcoords": g[use, 0].astype(np.float32),
        "n_chan": len(use),
    }


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("ap_bin", type=Path)
    p.add_argument("results_dir", type=Path)
    p.add_argument("--tmax", type=float, default=float("inf"), help="sort only the first N seconds")
    a = p.parse_args(argv)

    from kilosort import run_kilosort  # imported late: optional, heavy dependency

    meta_path = a.ap_bin.with_suffix(".meta")
    meta = read_meta(meta_path)
    probe = probe_from_meta(meta_path)
    # Everything else is the Kilosort default, which is what the lab has used so far.
    settings = {"n_chan_bin": int(meta["nSavedChans"]), "fs": float(meta["imSampRate"]), "tmax": a.tmax}
    print(f"{a.ap_bin.name}: {probe['n_chan']} channels, y {probe['yc'].min():g}..{probe['yc'].max():g} um")
    run_kilosort(settings, probe=probe, filename=a.ap_bin, results_dir=a.results_dir)


if __name__ == "__main__":
    main()
