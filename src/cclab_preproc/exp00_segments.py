"""exp00 movie task: TTL edges in nidq.bin -> one labelled row per movie segment.

exp00 sends no event codes, only pulses: one line at segment on, one at segment
off. Identity comes from ORDER: the k-th "on" edge is the k-th SegmentOn row of
event_log.csv. So the counts must match exactly, or every later segment would be
mislabelled; this stops with an error if they don't.

    uv run python -m cclab_preproc.exp00_segments <SpikeGLX run folder> <event_log.csv> <out.csv>

Output columns: trial, segment, movie (A/B), video, t_on_s / t_off_s (seconds
from the start of the nidq file), on_ap_sample / off_ap_sample (sample index in
the imec ap.bin = the units of Kilosort's spike_times.npy).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Rig wiring, read off the 2026-10-09 and 2026-10-10 recordings (NI digital word bits).
BIT_ON, BIT_OFF = 2, 0


def read_meta(path: Path) -> dict[str, str]:
    return dict(line.split("=", 1) for line in path.read_text().splitlines() if "=" in line)


def rising_edges(word: np.ndarray, bit: int) -> np.ndarray:
    b = (word >> bit) & 1
    return np.flatnonzero((b[:-1] == 0) & (b[1:] == 1)) + 1


def build(run_dir: Path, event_log: Path, bit_on: int = BIT_ON, bit_off: int = BIT_OFF) -> pd.DataFrame:
    ni_bin = next(run_dir.glob("*.nidq.bin"))
    ni = read_meta(ni_bin.with_suffix(".meta"))
    ap = read_meta(next(run_dir.glob("*_imec0/*.ap.meta")))
    ni_rate, im_rate = float(ni["niSampRate"]), float(ap["imSampRate"])
    nch = int(ni["nSavedChans"])
    word = np.memmap(ni_bin, dtype=np.int16, mode="r").reshape(-1, nch)[:, -1].astype(np.uint16)
    on, off = rising_edges(word, bit_on), rising_edges(word, bit_off)

    log = pd.read_csv(event_log)
    seg_on = log[log.event == "SegmentOn"].reset_index(drop=True)
    n_off = int((log.event == "SegmentOff").sum())
    if len(on) != len(seg_on) or len(off) != n_off or len(on) != len(off):
        raise SystemExit(
            f"TTL / event_log count mismatch: on edges {len(on)} vs SegmentOn {len(seg_on)}, "
            f"off edges {len(off)} vs SegmentOff {n_off}. Not labelling anything."
        )

    pairs = {
        int(r.trial): dict(kv.split("=") for kv in r.detail.split(";"))
        for r in log[log.event == "PairSelected"].itertuples()
    }
    movie = seg_on.detail.str.extract(r"movie=([AB])")[0]

    # ponytail: the SpikeGLX sync wave was off for these recordings, so NI -> imec uses
    # each stream's firstSample and calibrated rate from the meta files. Expect a few ms
    # of drift over a session; switch to the 1 Hz sync edges (TPrime) when it is recorded.
    def to_ap(i):
        return np.round((int(ni["firstSample"]) + i) / ni_rate * im_rate - int(ap["firstSample"])).astype(np.int64)

    return pd.DataFrame(
        {
            "trial": seg_on.trial.astype(int),
            "segment": seg_on.segment.astype(int),
            "movie": movie,
            "video": [pairs[int(t)][m] for t, m in zip(seg_on.trial, movie)],
            "t_on_s": on / ni_rate,
            "t_off_s": off / ni_rate,
            "on_ap_sample": to_ap(on),
            "off_ap_sample": to_ap(off),
        }
    )


if __name__ == "__main__":
    run_dir, event_log, out = map(Path, sys.argv[1:4])
    df = build(run_dir, event_log)
    dur = df.t_off_s - df.t_on_s
    assert (dur > 0).all(), "an off edge precedes its on edge"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"{len(df)} segments, {df.trial.nunique()} trials -> {out}")
    print(f"segment duration ms: median {dur.median() * 1e3:.1f}, range {dur.min() * 1e3:.1f}..{dur.max() * 1e3:.1f}")
