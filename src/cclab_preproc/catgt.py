"""CatGT pass 1 + supercat (pass 2): get SpikeGLX data ready for Kilosort.

This replaces ``scripts/catgt/pass1_for_supercat.bat`` and ``pass2_for_supercat.bat``:
the same CatGT command lines, but built from the session config so nothing has to
be edited per recording, and runnable on Windows or Linux.

* Pass 1 (once per task block): filter the AP band, global CAR, gfix artifact
  removal, extract sync edges -> ``<task>/processed/catgt/catgt_<run>_g<gate>/``.
* Pass 2 (supercat): join the pass-1 outputs of all task blocks into one
  continuous recording so they are spike-sorted together ->
  ``<session>/processed/supercat/supercat_<firstrun>_g<gate>/``.

CatGT reference: https://billkarsh.github.io/SpikeGLX/help/catgt_tshift/catgt_tshift/
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import Config, ConfigError
from .provenance import write_run_record

DEFAULTS = {
    "trigger": "0,0",
    "probes": "0",
    "prb_fld": False,
    "out_prb_fld": True,
    "ap": True,
    "lf": False,
    "ni": True,
    "apfilter": "butter,12,300,10000",
    "lffilter": "",
    "gblcar": True,
    "gfix": "0.40,0.10,0.02",
    "pass1_force_ni_ob_bin": True,
    "extra_args": [],
    "pass1_subdir": "processed/catgt",
    "supercat": True,
    "supercat_dir": "processed/supercat",
    "supercat_trim_edges": True,
    "supercat_extra_args": [],
}


@dataclass
class CatGTCommand:
    label: str
    args: list[str]
    dest: Path

    def shell(self, exe: str = "CatGT") -> str:
        return " ".join([exe, *(f'"{a}"' if " " in a else a for a in self.args)])


def _settings(cfg: Config) -> dict:
    s = dict(DEFAULTS)
    if "catgt" in cfg.steps:
        unknown = set(cfg.steps["catgt"]) - set(DEFAULTS) - {"tasks"}
        if unknown:
            raise ConfigError(f"[catgt] has unknown keys: {sorted(unknown)}")
        s.update(cfg.steps["catgt"])
    s["supercat_dir"] = cfg.resolve(s["supercat_dir"])
    return s


def _tasks(cfg: Config, s: dict) -> list:
    names = s.get("tasks") or [t.name for t in cfg.tasks if t.spikeglx_run]
    tasks = [cfg.task(n) for n in names]
    for t in tasks:
        if not t.spikeglx_run:
            raise ConfigError(f"Task {t.name!r} needs spikeglx_run to be processed by CatGT.")
    if not tasks:
        raise ConfigError("No task blocks with spikeglx_run set; nothing for CatGT to do.")
    return tasks


def _stream_args(s: dict) -> list[str]:
    args = []
    if s["ap"]:
        args.append("-ap")
    if s["lf"]:
        args.append("-lf")
    if s["ni"]:
        args.append("-ni")
    args.append(f"-prb={s['probes']}")
    return args


def pass1_commands(cfg: Config) -> list[CatGTCommand]:
    s = _settings(cfg)
    cmds = []
    for t in _tasks(cfg, s):
        dest = cfg.task_dir(t.name) / s["pass1_subdir"]
        args = [
            f"-dir={cfg.raw_dir(t.name)}",
            f"-run={t.spikeglx_run}",
            f"-g={t.gate}",
            f"-t={s['trigger']}",
            *_stream_args(s),
        ]
        if s["prb_fld"]:
            args.append("-prb_fld")
        if s["apfilter"]:
            args.append(f"-apfilter={s['apfilter']}")
        if s["lffilter"]:
            args.append(f"-lffilter={s['lffilter']}")
        if s["gblcar"]:
            args.append("-gblcar")
        if s["gfix"]:
            args.append(f"-gfix={s['gfix']}")
        if s["out_prb_fld"]:
            args.append("-out_prb_fld")
        if s["ni"] and s["pass1_force_ni_ob_bin"]:
            args.append("-pass1_force_ni_ob_bin")
        args += list(s["extra_args"])
        args.append(f"-dest={dest}")
        cmds.append(CatGTCommand(f"pass1 {t.name}", args, dest))
    return cmds


def supercat_command(cfg: Config) -> CatGTCommand | None:
    s = _settings(cfg)
    tasks = _tasks(cfg, s)
    if not s["supercat"] or len(tasks) < 2:
        return None
    elements = "".join(
        f"{{{cfg.task_dir(t.name) / s['pass1_subdir']},catgt_{t.spikeglx_run}_g{t.gate}}}"
        for t in tasks
    )
    args = [f"-supercat={elements}", *_stream_args(s)]
    if s["supercat_trim_edges"]:
        args.append("-supercat_trim_edges")
    args += list(s["supercat_extra_args"])
    dest = s["supercat_dir"]
    args.append(f"-dest={dest}")
    return CatGTCommand("pass2 supercat", args, dest)


def all_commands(cfg: Config) -> list[CatGTCommand]:
    cmds = pass1_commands(cfg)
    sc = supercat_command(cfg)
    return cmds + ([sc] if sc else [])


def kilosort_input(cfg: Config) -> Path:
    """Folder that holds the .ap.bin to give Kilosort after CatGT has run."""
    s = _settings(cfg)
    tasks = _tasks(cfg, s)
    first = tasks[0]
    if supercat_command(cfg) is not None:
        return Path(s["supercat_dir"]) / f"supercat_{first.spikeglx_run}_g{first.gate}"
    return cfg.task_dir(first.name) / s["pass1_subdir"] / f"catgt_{first.spikeglx_run}_g{first.gate}"


def find_catgt(cfg: Config) -> Path:
    exe = cfg.local.get("catgt_path") or shutil.which("CatGT") or shutil.which("runit.sh")
    if not exe:
        raise ConfigError(
            "CatGT not found. Set catgt_path in configs/local.toml (path to CatGT.exe on "
            "Windows or runit.sh on Linux) or the CCLAB_CATGT environment variable."
        )
    exe = Path(exe).expanduser()
    if not exe.exists():
        raise ConfigError(f"catgt_path does not exist: {exe}")
    return exe


def run(cfg: Config, execute: bool = False, only: str | None = None) -> list[CatGTCommand]:
    """Print (default) or execute the CatGT commands for a session.

    ``only`` = "pass1" or "supercat" to run one stage.
    """
    cmds = all_commands(cfg)
    if only == "pass1":
        cmds = [c for c in cmds if c.label.startswith("pass1")]
    elif only == "supercat":
        cmds = [c for c in cmds if c.label.startswith("pass2")]

    exe = find_catgt(cfg) if execute else Path(cfg.local.get("catgt_path") or "CatGT")
    for c in cmds:
        print(f"\n# {c.label}\n{c.shell(str(exe))}")
        if any(" " in a for a in c.args):
            print("# WARNING: CatGT does not handle spaces in paths well; consider renaming.")
    if not execute:
        print("\n(dry run: add --run to execute)")
        return cmds

    for c in cmds:
        c.dest.mkdir(parents=True, exist_ok=True)
        write_run_record(cfg, c.dest, "catgt", {"label": c.label, "args": c.args})
        print(f"\n>>> {c.label}")
        # CatGT writes CatGT.log next to itself, like the original .bat files.
        result = subprocess.run([str(exe), *c.args], cwd=exe.parent)
        log = exe.parent / "CatGT.log"
        if log.exists():
            shutil.copy2(log, c.dest / f"CatGT_{c.label.replace(' ', '_')}.log")
        if result.returncode != 0:
            raise RuntimeError(f"CatGT failed during {c.label} (exit {result.returncode}); see CatGT.log")
    print(f"\nDone. Kilosort input: {kilosort_input(cfg)}")
    return cmds
