"""Python port of matlab/BuildRecordingMeta.m.

Assembles ONE standardized ``<task>.mat`` per recording task block (CC Lab Data
Organization Standard, section 5) from Kilosort/Phy output, the synced event
codes and the behavioral file. Everything is on the neural clock, in seconds.

    meta.info    provenance + session metadata
    meta.spikes  per-unit cluster metadata + spike-time cells (seconds)
    meta.trials  one row per ATTEMPTED trial, aligned to the neural clock
    meta.events  raw synced event streams (trial start / attempt, all codes)
    meta.lfp     placeholder (not yet added)

Conventions (same as the MATLAB version):
  - spike_times.npy are SAMPLES at sampling_rate (30 kHz) -> seconds = / sr
  - sync_event_codes.npy column 2 is MILLISECONDS on the neural clock -> / 1000
  - event code 4 = trial start, event code 1 = trial attempt (alignment)
  - unit inclusion = KSLabel in {good, mua}  (set label_column = "group" to use
    the Phy curation labels instead)
"""

from __future__ import annotations

import datetime as _dt
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import scipy.io as sio

from .config import Config, ConfigError
from .provenance import write_run_record

BUILDER_VERSION = "py-0.1.0"

DEFAULTS: dict[str, Any] = {
    "ks_dir": "processed/kilosort4",
    "sync_events_file": "processed/events/sync_event_codes.npy",
    "behavior_file": "",
    "out_file": "",  # default: <task folder>/<task>.mat
    "sampling_rate": 30000,
    "lfp_fs": 1250,
    "inclusion": ["good", "mua"],
    "label_column": "KSLabel",
    "code_start": 4,
    "code_attempt": 1,
    "n_target_pos": 8,
}


def settings(cfg: Config) -> dict[str, Any]:
    if "meta" not in cfg.steps:
        raise ConfigError(f"{cfg.path.name} has no [meta] section.")
    raw = cfg.steps["meta"]
    if "task" not in raw:
        raise ConfigError("[meta] needs task = \"<task block name>\".")
    unknown = set(raw) - set(DEFAULTS) - {"task"}
    if unknown:
        raise ConfigError(f"[meta] has unknown keys: {sorted(unknown)}")
    task_dir = cfg.task_dir(raw["task"])
    s = {**DEFAULTS, **raw}
    for key in ("ks_dir", "sync_events_file", "behavior_file", "out_file"):
        s[key] = cfg.resolve(s[key], task_dir) if s[key] else None
    if s["out_file"] is None:
        s["out_file"] = task_dir / f"{raw['task']}.mat"
    return s


# --- pieces -------------------------------------------------------------------
def load_spikes(ks_dir: Path, sampling_rate: float, inclusion: list[str], label_column: str):
    """Per-unit metadata + spike-time arrays (seconds) for included units."""
    st = np.load(ks_dir / "spike_times.npy").astype(np.float64).ravel()
    sc = np.load(ks_dir / "spike_clusters.npy").astype(np.int64).ravel()
    ci = pd.read_csv(ks_dir / "cluster_info.tsv", sep="\t")
    if label_column not in ci.columns:
        raise ConfigError(
            f"cluster_info.tsv has no {label_column!r} column (columns: {list(ci.columns)}). "
            "Open the sort in Phy and save once to create it."
        )

    keep = ci[label_column].isin(inclusion).to_numpy()
    sub = ci[keep]
    uid = sub["cluster_id"].to_numpy()

    order = np.argsort(sc, kind="stable")
    sc_sorted, st_sorted = sc[order], st[order] / sampling_rate
    cells = []
    for u in uid:
        lo, hi = np.searchsorted(sc_sorted, [u, u + 1])
        cells.append(np.sort(st_sorted[lo:hi]))

    def col(name):
        return sub[name].to_numpy() if name in sub.columns else np.full(len(sub), np.nan)

    spikes = {
        "cluster_ids": uid,
        "depths": col("depth"),
        "ch_best": col("ch"),
        "ks_labels": sub[label_column].astype(str).tolist(),
        "n_spikes": col("n_spikes"),
        "contam_pct": col("ContamPct"),
        "firing_rate": col("fr"),
        "spike_times_cell": cells,
    }
    return spikes, len(uid)


def load_events(sync_file: Path, code_start: int, code_attempt: int):
    """Trial-start / trial-attempt streams (seconds) + the full synced code stream."""
    sec = np.load(sync_file).astype(np.float64)  # (N, 2) [code, time_ms]
    codes, tsec = sec[:, 0], sec[:, 1] / 1000.0
    events = {
        "trial_start_times": np.unique(tsec[codes == code_start]),
        "trial_attempt_times": np.unique(tsec[codes == code_attempt]),
        "event_codes": codes,
        "event_times_s": tsec,
    }
    return events, events["trial_attempt_times"]


def make_valid_name(label: str) -> str:
    """Approximation of MATLAB's matlab.lang.makeValidName."""
    words = label.strip().split()
    name = words[0] + "".join(w[:1].upper() + w[1:] for w in words[1:]) if words else "x"
    name = re.sub(r"\W", "_", name)
    return name if re.match(r"[A-Za-z]", name) else "x" + name


def read_behavior_table(behavior_file: Path) -> pd.DataFrame:
    """Read the PsychToolbox ``Results`` struct (labels + data) into a DataFrame.

    MATLAB ``table`` objects can't be read outside MATLAB; save them as a struct or
    use the MATLAB builder for those sessions.
    """
    S = sio.loadmat(behavior_file, squeeze_me=True, struct_as_record=False)
    if "Results" not in S:
        raise ConfigError(
            f"{behavior_file.name}: no 'Results' struct found (variables: "
            f"{[k for k in S if not k.startswith('__')]}). MATLAB tables can't be read from "
            "Python; use matlab/BuildRecordingMeta.m for this session."
        )
    R = S["Results"]
    labels = [make_valid_name(str(x)) for x in np.atleast_1d(R.labels)]
    cols = [np.asarray(c, dtype=float).ravel() for c in np.atleast_1d(R.data)]
    return pd.DataFrame(dict(zip(labels, cols)))


def assign_group_mgs(x: float, y: float, npos: int) -> int:
    """Map a target (x, y) to a direction group 1..npos (same as assignGroupMGS)."""
    ang = round(np.degrees(np.arctan2(y, x)))
    if npos == 8:
        keys, vals = [45, 0, -45, -90, -135, 180, 135, 90], [1, 2, 3, 4, 5, 6, 7, 8]
    else:
        keys, vals = [45, 0, -45, -135, 180, 135], [1, 2, 3, 4, 5, 6]
    d = np.abs(np.mod(ang - np.array(keys) + 180, 360) - 180)  # circular nearest key
    return vals[int(np.argmin(d))]


def load_behavior(behavior_file: Path, attempt_times: np.ndarray, n_target_pos: int):
    """Keep ATTEMPTED trials, align them to neural attempt times, add target_group."""
    tb = read_behavior_table(behavior_file)
    att = tb[tb["TrialAttemp"] == 1]
    if len(att) != len(attempt_times):
        raise ValueError(
            f"Alignment mismatch: {len(att)} attempted behavioral trials vs "
            f"{len(attempt_times)} neural attempt events. Inspect before trusting this session."
        )
    x, y = att["x_sp"].to_numpy(float), att["y_sp"].to_numpy(float)
    return {
        "attempt_time": np.asarray(attempt_times, float),
        "trial_success": att["TrialSuccess"].to_numpy(float),
        "x_sp": x,
        "y_sp": y,
        "reward_amount": att["RewardAmount"].to_numpy(float),
        "target_group": np.array([assign_group_mgs(a, b, n_target_pos) for a, b in zip(x, y)], float),
    }


def empty_trials() -> dict[str, np.ndarray]:
    z = np.zeros(0)
    return {k: z for k in ("attempt_time", "trial_success", "target_group", "x_sp", "y_sp", "reward_amount")}


# --- assembly -----------------------------------------------------------------
def build(cfg: Config, save: bool = True) -> dict[str, Any]:
    """Build the metafile for the task named in the config's [meta] section."""
    s = settings(cfg)
    task = s["task"]

    spikes, n_units = load_spikes(s["ks_dir"], s["sampling_rate"], s["inclusion"], s["label_column"])
    events, attempt_times = load_events(s["sync_events_file"], s["code_start"], s["code_attempt"])
    trials = (
        load_behavior(s["behavior_file"], attempt_times, s["n_target_pos"])
        if s["behavior_file"]
        else empty_trials()
    )

    info = {
        "subject": cfg.animal,
        "date": cfg.date,
        "area": cfg.area,
        "probe": cfg.probe,
        "task": task,
        "session_id": cfg.session_id,
        "sampling_rate": s["sampling_rate"],
        "lfp_fs": s["lfp_fs"],
        "timebase": "seconds, neural (Kilosort AP) clock",
        "unit_inclusion": f"{s['label_column']} in {{{','.join(s['inclusion'])}}}",
        "n_units": n_units,
        "n_trials_attempted": len(trials["trial_success"]),
        "n_trials_success": int(np.sum(trials["trial_success"] == 1)),
        "source_files": {
            "ks_dir": str(s["ks_dir"]),
            "sync_events": str(s["sync_events_file"]),
            "behavior_mat": str(s["behavior_file"] or ""),
            "config": str(cfg.path),
        },
        "builder_version": BUILDER_VERSION,
        "built_on": _dt.datetime.now().isoformat(timespec="seconds"),
        "notes": "",
    }
    lfp = {"data": np.zeros((0, 0)), "fs": s["lfp_fs"], "channel_map": np.zeros(0),
           "channel_positions": np.zeros((0, 0)), "status": "not_yet_added"}
    meta = {"info": info, "spikes": spikes, "trials": trials, "events": events, "lfp": lfp}

    if save:
        out = Path(s["out_file"])
        out.parent.mkdir(parents=True, exist_ok=True)
        sio.savemat(out, {"meta": _to_matlab(meta)}, do_compression=True, long_field_names=True)
        # run record goes in processed/_runs so the task folder keeps the standard layout
        write_run_record(cfg, cfg.processed_dir(task), "build_meta", {"out_file": str(out)})
        print(
            f"Built {cfg.session_id} / {task}: {n_units} units, "
            f"{info['n_trials_attempted']} attempted / {info['n_trials_success']} success\n"
            f"Saved -> {out}"
        )
    return meta


def _to_matlab(obj):
    """Convert nested dicts/lists into types scipy.io.savemat writes as struct/cell."""
    if isinstance(obj, dict):
        return {k: _to_matlab(v) for k, v in obj.items()}
    if isinstance(obj, list):
        cell = np.empty((len(obj), 1), dtype=object)
        for i, v in enumerate(obj):
            cell[i, 0] = np.asarray(v).reshape(-1, 1) if isinstance(v, np.ndarray) else v
        return cell
    if isinstance(obj, np.ndarray) and obj.ndim == 1:
        return obj.reshape(-1, 1)  # column vectors, like the MATLAB builder
    return obj


def load_meta(path: str | Path) -> dict[str, Any]:
    """Read a <task>.mat metafile back into nested Python objects."""
    return sio.loadmat(path, squeeze_me=True, struct_as_record=False, simplify_cells=True)["meta"]


def psth(spike_times: np.ndarray, align_times: np.ndarray, window=(-0.5, 1.5), bin_s=0.01):
    """Trial x time spike-count PSTH (Hz) of one unit around ``align_times`` (seconds)."""
    edges = np.arange(window[0], window[1] + bin_s / 2, bin_s)
    counts = np.array([np.histogram(spike_times - t, bins=edges)[0] for t in align_times])
    return counts / bin_s, edges[:-1] + bin_s / 2
