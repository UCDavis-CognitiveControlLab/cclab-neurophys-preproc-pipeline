"""exp00 sanity check: firing rate around segment onset, from Kilosort output + segments.csv.

    uv run python -m cclab_preproc.exp00_psth <kilosort4 folder> <segments.csv> <out.png>

A visual response after segment onset (strongest at segment 1 A, which follows a
blank screen) means sorting and alignment both work. A flat picture means the
alignment is wrong before it means anything about the brain.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

FS = 30000.0  # only used to turn a sample window into seconds; spikes and events are both in ap samples
PRE, POST, BIN = 0.5, 2.5, 0.02


def psth(spikes: np.ndarray, events: np.ndarray, edges: np.ndarray) -> np.ndarray:
    """Mean rate (Hz) per bin; spikes must be sorted. All arguments in samples."""
    counts = np.zeros(len(edges) - 1)
    for e in events:
        lo, hi = np.searchsorted(spikes, [e + edges[0], e + edges[-1]])
        counts += np.histogram(spikes[lo:hi] - e, edges)[0]
    return counts / len(events) / (BIN)


if __name__ == "__main__":
    ks, seg_csv, out = map(Path, sys.argv[1:4])
    st = np.load(ks / "spike_times.npy").astype(np.int64).ravel()
    sc = np.load(ks / "spike_clusters.npy").ravel()
    labels = pd.read_csv(ks / "cluster_KSLabel.tsv", sep="\t")
    good = labels.cluster_id[labels.KSLabel == "good"].to_numpy()
    seg = pd.read_csv(seg_csv)
    edges = np.round(np.arange(-PRE, POST + 1e-9, BIN) * FS).astype(np.int64)
    t = (edges[:-1] + edges[1:]) / 2 / FS

    first = seg[(seg.segment == 1) & (seg.movie == "A")].on_ap_sample.to_numpy()
    later = seg[~((seg.segment == 1) & (seg.movie == "A"))].on_ap_sample.to_numpy()
    order = np.argsort(sc, kind="stable")
    st_by, sc_by = st[order], sc[order]
    starts = np.searchsorted(sc_by, good)
    stops = np.searchsorted(sc_by, good, side="right")
    R1 = np.array([psth(st_by[a:b], first, edges) for a, b in zip(starts, stops)])
    R2 = np.array([psth(st_by[a:b], later, edges) for a, b in zip(starts, stops)])

    base = t < 0
    z = (R1 - R1[:, base].mean(1, keepdims=True)) / (R1[:, base].std(1, keepdims=True) + 1e-9)
    peak = np.abs(z[:, (t > 0.03) & (t < 0.4)]).max(1)

    fig, ax = plt.subplots(1, 2, figsize=(12, 5))
    ax[0].plot(t, R1.mean(0), label=f"segment 1 A onset (n={len(first)})")
    ax[0].plot(t, R2.mean(0), label=f"all other onsets (n={len(later)})")
    ax[0].axvline(0, color="k", lw=0.5)
    ax[0].set(xlabel="time from segment-on TTL (s)", ylabel="mean rate, good units (Hz)")
    ax[0].legend()
    im = ax[1].imshow(z[np.argsort(-peak)], aspect="auto", extent=[t[0], t[-1], len(good), 0], vmin=-5, vmax=5, cmap="RdBu_r")
    ax[1].axvline(0, color="k", lw=0.5)
    ax[1].set(xlabel="time from segment 1 A onset (s)", ylabel="good units, sorted by response size")
    fig.colorbar(im, ax=ax[1], label="z vs pre-onset baseline")
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    print(f"{len(good)} good units, {len(st)} spikes -> {out}")
    print(f"units with |z| > 5 in 30-400 ms after segment 1 A onset: {(peak > 5).sum()} / {len(good)}")
