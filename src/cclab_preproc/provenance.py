"""Archive exactly what produced an output folder.

Every step calls :func:`write_run_record` on its output folder. That writes
``_runs/<timestamp>_<step>/`` containing a verbatim copy of the session config and
a ``run.json`` with the git commit, package versions, machine and user.
"""

from __future__ import annotations

import datetime as _dt
import getpass
import json
import platform
import subprocess
import sys
from importlib import metadata
from pathlib import Path
from typing import Any

from .config import REPO_ROOT, Config

_PACKAGES = ("cclab-preproc", "numpy", "scipy", "pandas", "scikit-learn", "matplotlib")


def git_info() -> dict[str, Any]:
    def run(*args: str) -> str | None:
        try:
            return subprocess.run(
                ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True
            ).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return None

    return {
        "commit": run("rev-parse", "HEAD"),
        "dirty": bool(run("status", "--porcelain")),
    }


def write_run_record(cfg: Config, out_dir: Path, step: str, extra: dict | None = None) -> Path:
    """Write the config copy + run.json into ``out_dir/_runs/...`` and return that folder."""
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = Path(out_dir) / "_runs" / f"{stamp}_{step}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / cfg.path.name).write_text(cfg.text)

    versions = {}
    for pkg in _PACKAGES:
        try:
            versions[pkg] = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            pass

    record = {
        "step": step,
        "session_id": cfg.session_id,
        "config_file": str(cfg.path),
        "started": _dt.datetime.now().isoformat(timespec="seconds"),
        "user": getpass.getuser(),
        "machine": platform.node(),
        "python": sys.version.split()[0],
        "git": git_info(),
        "versions": versions,
        "data_root": str(cfg.data_root) if cfg.data_root else None,
        **(extra or {}),
    }
    (run_dir / "run.json").write_text(json.dumps(record, indent=2, default=str))
    if record["git"]["dirty"]:
        print(
            "Note: the pipeline repo has uncommitted changes; run.json records the "
            "commit but not your local edits."
        )
    return run_dir
