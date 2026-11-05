from pathlib import Path

import numpy as np
import pytest

from cclab_preproc import ConfigError, load_config
from cclab_preproc import catgt, meta
from cclab_preproc.cli import main
from cclab_preproc.config import REPO_ROOT
from cclab_preproc.demo import make_demo


@pytest.fixture
def demo(tmp_path):
    return make_demo(tmp_path), tmp_path


def write(tmp_path, text, name="venni_20250731_SEF.toml"):
    p = tmp_path / name
    p.write_text(text)
    return p


BASE = """
[session]
animal = "venni"
date = "2025-07-31"
area = "SEF"
probe = "npx"

[[tasks]]
name = "mgs"
spikeglx_run = "MGS1"
"""


def test_session_id_and_standard_paths(tmp_path):
    cfg = load_config(write(tmp_path, BASE), data_root=tmp_path)
    assert cfg.session_id == "venni_20250731_SEF"
    assert cfg.session_dir == tmp_path / "neuropixel" / "venni" / "venni_20250731_SEF"
    assert cfg.raw_dir("mgs") == cfg.session_dir / "mgs" / "raw"


@pytest.mark.parametrize("field,bad", [("animal", "Vennie"), ("area", "sef"), ("probe", "neuropixels"), ("date", "073125")])
def test_vocabulary_is_enforced(tmp_path, field, bad):
    text = BASE.replace({"animal": '"venni"', "area": '"SEF"', "probe": '"npx"', "date": '"2025-07-31"'}[field], f'"{bad}"', 1)
    with pytest.raises(ConfigError):
        load_config(write(tmp_path, text), data_root=tmp_path)


def test_step_paths_relative_and_absolute(tmp_path):
    text = BASE + """
[mi_classification]
task = "mgs"
psth_dir = "derivatives/psth"
mat_dir = 'D:\\legacy\\matlab'
n_jobs = 4
"""
    cfg = load_config(write(tmp_path, text), data_root=tmp_path)
    s = cfg.step("mi_classification")
    assert s["psth_dir"] == cfg.task_dir("mgs") / "derivatives" / "psth"
    assert str(s["mat_dir"]).startswith("D:")
    assert s["n_jobs"] == 4


def test_absolute_paths_need_no_data_root(tmp_path, monkeypatch):
    monkeypatch.delenv("CCLAB_DATA_ROOT", raising=False)
    monkeypatch.setattr("cclab_preproc.config.LOCAL_CONFIG", tmp_path / "missing.toml")
    text = BASE + '\n[mi_classification]\ntask = "mgs"\npsth_dir = "/abs/psth"\n'
    s = load_config(write(tmp_path, text)).step("mi_classification")
    assert s["psth_dir"] == Path("/abs/psth")


def test_unknown_task_reference(tmp_path):
    with pytest.raises(ConfigError, match="not listed"):
        load_config(write(tmp_path, BASE + '\n[meta]\ntask = "mgs2"\n'), data_root=tmp_path)


def test_catgt_matches_original_bat(demo):
    cfg_path, root = demo
    cfg = load_config(cfg_path, data_root=root)
    p1 = catgt.pass1_commands(cfg)
    assert [c.label for c in p1] == ["pass1 mgs", "pass1 FV"]
    args = p1[0].args
    # the flags from scripts/catgt/pass1_for_supercat.bat
    for flag in ["-run=MGS1", "-g=0", "-t=0,0", "-ap", "-prb=0", "-apfilter=butter,12,300,10000",
                 "-gblcar", "-gfix=0.40,0.10,0.02", "-out_prb_fld", "-ni", "-pass1_force_ni_ob_bin"]:
        assert flag in args
    assert args[0] == f"-dir={cfg.raw_dir('mgs')}"
    sc = catgt.supercat_command(cfg)
    assert sc.args[0].startswith("-supercat={") and "catgt_FV1_g0}" in sc.args[0]
    assert "-supercat_trim_edges" in sc.args
    assert catgt.kilosort_input(cfg).name == "supercat_MGS1_g0"


def test_single_task_has_no_supercat(tmp_path):
    cfg = load_config(write(tmp_path, BASE), data_root=tmp_path)
    assert catgt.supercat_command(cfg) is None
    assert catgt.kilosort_input(cfg).name == "catgt_MGS1_g0"


def test_build_meta_roundtrip(demo):
    cfg_path, root = demo
    cfg = load_config(cfg_path, data_root=root)
    built = meta.build(cfg)
    out = cfg.task_dir("mgs") / "mgs.mat"
    assert out.exists()
    m = meta.load_meta(out)
    assert m["info"]["session_id"] == "venni_20250731_SEF"
    assert m["info"]["n_units"] == len(m["spikes"]["cluster_ids"]) == built["info"]["n_units"]
    assert set(m["spikes"]["ks_labels"]) <= {"good", "mua"}
    assert len(m["trials"]["attempt_time"]) == m["info"]["n_trials_attempted"] == 80
    assert set(np.unique(m["trials"]["target_group"])) <= set(range(1, 9))
    # provenance archived
    runs = list((cfg.processed_dir("mgs") / "_runs").glob("*_build_meta"))
    assert runs and (runs[0] / "venni_20250731_SEF.toml").exists() and (runs[0] / "run.json").exists()


def test_assign_group_matches_matlab_table():
    expected = {45: 1, 0: 2, -45: 3, -90: 4, -135: 5, 180: 6, 135: 7, 90: 8}
    for ang, g in expected.items():
        r = np.deg2rad(ang)
        assert meta.assign_group_mgs(np.cos(r), np.sin(r), 8) == g


def test_example_configs_load():
    for p in (REPO_ROOT / "configs").glob("*/*.toml"):
        load_config(p, data_root="/data")


def test_cli_new_config(tmp_path, monkeypatch):
    monkeypatch.setattr("cclab_preproc.cli.REPO_ROOT", tmp_path)
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs" / "_template.toml").write_text((REPO_ROOT / "configs" / "_template.toml").read_text())
    main(["new-config", "--animal", "isaac", "--date", "20260324", "--area", "FEF", "--probe", "npx",
          "--task", "mgs:MGS1", "--task", "FV:FV1"])
    cfg = load_config(tmp_path / "configs" / "npx" / "isaac_20260324_FEF.toml", data_root=tmp_path)
    assert [t.spikeglx_run for t in cfg.tasks] == ["MGS1", "FV1"]
    assert cfg.steps["meta"]["task"] == "mgs"
