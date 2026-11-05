"""Run every notebook top to bottom on small synthetic data (few permutations).

Checks that the notebooks are runnable from a config, not that the science is right.
Skip with:  uv run pytest -m "not notebooks"
"""

import os
from pathlib import Path

import nbformat
import numpy as np
import pytest
import scipy.io as sio
from nbconvert.preprocessors import ExecutePreprocessor

from cclab_preproc.config import REPO_ROOT
from cclab_preproc.demo import make_demo

pytestmark = pytest.mark.notebooks

SESSION = """
[session]
animal = "venni"
date = "20250101"
area = "SEF"
probe = "{probe}"

[[tasks]]
name = "mgs"
"""

STATS = "n_permutations = 5\nn_neighbors = 5\nalpha = 0.05\nn_jobs = 2\n"


def make_npx(d: Path, rng) -> Path:
    nN, T = 8, 230
    angs, dist = [], []
    for dv in (0.0, 45.0, 180.0):
        nt = 48
        a = np.tile(np.arange(1, 9), nt // 8)
        angs.append(a)
        dist.append(np.full(nt, dv))
        ps = rng.poisson(5, (nN, nt, T)).astype(float)
        ps[:4, :, 55:80] += 10 * (a[None, :, None] == 3)
        sio.savemat(d / f"psth_{int(dv)}.mat", {"psth_3d": ps})
        sio.savemat(d / f"sacc_{int(dv)}.mat", {"saccadeTimes": rng.uniform(0.3, 0.5, (1, nt))})
    np.save(d / "angs.npy", np.concatenate(angs))
    np.save(d / "dist.npy", np.concatenate(dist))
    np.save(d / "good.npy", np.arange(nN))
    sio.savemat(d / "tau.mat", {"tau_values": rng.uniform(50, 300, (1, nN))})
    cfg = d / "npx.toml"
    cfg.write_text(SESSION.format(probe="npx") + f"""
[mi_classification]
task = "mgs"
psth_dir = "{d}"
mat_dir = "{d}"
out_dir = "{d}/out"
output_suffix = ""
psth_files = {{ 0 = "psth_0.mat", 45 = "psth_45.mat", 180 = "psth_180.mat" }}
saccade_files = {{ 0 = "sacc_0.mat", 45 = "sacc_45.mat", 180 = "sacc_180.mat" }}
angs_name = "angs.npy"
distractor_name = "dist.npy"
good_neurons_name = "good.npy"
tau_name = "tau.mat"
psth_start_ms = -500
psth_end_ms = 1800
bin_ms = 10
saccade_offset_s = 0.9
sacc_pre_ms = 400
sacc_post_ms = 400
baseline_bins = [0, 50]
visual_bins = [55, 80]
memory_bins = [80, 120]
motor_bins = [30, 45]
min_rate = 3
{STATS}""")
    return cfg


def make_ripple(d: Path, rng) -> Path:
    nE, nt, T = 4, 48, 300
    a = np.tile(np.arange(1, 9), nt // 8)
    ps = rng.poisson(5, (nE, nt, T)).astype(float)
    ps[:2, :, 50:90] += 8 * (a[None, :, None] == 2)
    sio.savemat(d / "psth.mat", {"psth_3d": ps})
    sio.savemat(d / "targetAng.mat", {"targetAng": a[None, :]})
    sio.savemat(d / "sacc.mat", {"saccadeTimes": rng.uniform(0.3, 0.5, (1, nt))})
    sio.savemat(d / "tau.mat", {"tau_values": rng.uniform(50, 300, (1, nE))})
    cfg = d / "ripple.toml"
    cfg.write_text(SESSION.format(probe="ripple") + f"""
[mi_classification]
task = "mgs"
psth_dir = "{d}"
mat_dir = "{d}"
out_dir = "{d}/out"
output_suffix = "_test"
psth_name = "psth.mat"
target_angle_name = "targetAng.mat"
saccade_name = "sacc.mat"
tau_name = "tau.mat"
channel_names = [1, 17, 2, 18]
psth_start_ms = -500
psth_end_ms = 2500
bin_ms = 10
saccade_offset_s = 1.1
sacc_pre_ms = 1000
sacc_post_ms = 1000
baseline_bins = [20, 50]
visual_bins = [50, 90]
memory_bins = [90, 130]
motor_bins = [80, 110]
post_saccade_bins = [130, 180]
n_cv_folds = 5
min_rate = 0
{STATS}""")
    return cfg


def execute(notebook: str, config: Path, monkeypatch, data_root: Path | None = None):
    monkeypatch.setenv("CCLAB_CONFIG", str(config))
    monkeypatch.setenv("MPLBACKEND", "Agg")
    if data_root:
        monkeypatch.setenv("CCLAB_DATA_ROOT", str(data_root))
    nb = nbformat.read(REPO_ROOT / "notebooks" / notebook, as_version=4)
    ExecutePreprocessor(timeout=600, kernel_name="python3").preprocess(
        nb, {"metadata": {"path": str(REPO_ROOT / "notebooks")}}
    )


def test_neuropixels_notebook(tmp_path, monkeypatch):
    cfg = make_npx(tmp_path, np.random.default_rng(0))
    execute("Neuropix_Processing_MI_Timescale.ipynb", cfg, monkeypatch)
    assert (tmp_path / "out" / "results_MI_Timescale.pkl").exists()
    assert list((tmp_path / "out" / "_runs").iterdir())


def test_ripple_notebook(tmp_path, monkeypatch):
    cfg = make_ripple(tmp_path, np.random.default_rng(0))
    execute("Ripple_Processing_MI_Timescale.ipynb", cfg, monkeypatch)
    assert (tmp_path / "out" / "results_MI_Timescale_test.pkl").exists()


def test_build_meta_notebook(tmp_path, monkeypatch):
    cfg = make_demo(tmp_path)
    execute("Build_Recording_Meta.ipynb", cfg, monkeypatch, data_root=tmp_path)
    assert (tmp_path / "neuropixel" / "venni" / "venni_20250731_SEF" / "mgs" / "mgs.mat").exists()
