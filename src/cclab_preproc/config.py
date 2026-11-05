"""Per-session experiment configs.

One TOML file per recording session lives in ``configs/<probe>/<session_id>.toml``.
It describes *what* was recorded (animal, date, area, probe, task blocks) and the
settings for each pipeline step. *Where* the data lives on a given machine comes
from ``configs/local.toml`` (not committed), so the same config works on every
lab computer and can be archived alongside the results it produced.

Folder layout follows the CC Lab Data Organization Standard::

    <data_root>/<probe folder>/<animal>/<session_id>/<task>/{raw,processed,derivatives}

See docs/configuration.md for the full reference.
"""

from __future__ import annotations

import datetime as _dt
import os
import re
import tomllib
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
LOCAL_CONFIG = REPO_ROOT / "configs" / "local.toml"

# --- Controlled vocabulary (CC Lab Data Organization Standard, section 1) -----
# Add new entries here (and to docs/configuration.md) when the lab adopts them.
ANIMALS = {"venni", "isaac"}
AREAS = {"SEF", "FEF"}
# probe token -> top-level folder name under the data root (standard, section 2.1)
PROBE_FOLDERS = {"npx": "neuropixel", "sprobe": "plexon", "ripple": "ripple"}
TASKS = {"mgs", "mgsVarDelay", "mgsDiffDir", "FV", "RF"}

# Keys with these suffixes inside a step section are treated as paths.
PATH_SUFFIXES = ("_dir", "_file", "_path")


class ConfigError(ValueError):
    """Raised when a config file is missing information or uses unknown values."""


@dataclass
class Task:
    """One task block (one acquisition run) within a session."""

    name: str  # folder name, e.g. "mgs", "mgs2", "FV", "mgs+stim"
    spikeglx_run: str | None = None  # SpikeGLX run name, e.g. "MGS2" for raw/MGS2_g0
    gate: int = 0
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class Config:
    path: Path
    text: str  # original file contents, archived verbatim with every run
    animal: str
    date: str  # YYYYMMDD
    area: str
    probe: str
    tasks: list[Task]
    session: dict[str, Any]
    steps: dict[str, dict[str, Any]]
    data_root: Path | None
    local: dict[str, Any]

    # --- identifiers -------------------------------------------------------
    @property
    def session_id(self) -> str:
        """``<animal>_<YYYYMMDD>_<area>``, e.g. ``venni_20250731_SEF``."""
        return f"{self.animal}_{self.date}_{self.area}"

    # --- standard folders ----------------------------------------------------
    def _require_root(self) -> Path:
        if self.data_root is None:
            raise ConfigError(
                "No data root set. Copy configs/local.example.toml to configs/local.toml "
                "and set data_root, or set the CCLAB_DATA_ROOT environment variable."
            )
        return self.data_root

    @property
    def probe_dir(self) -> Path:
        return self._require_root() / PROBE_FOLDERS[self.probe]

    @property
    def sessions_csv(self) -> Path:
        return self.probe_dir / "sessions.csv"

    @property
    def session_dir(self) -> Path:
        return self.probe_dir / self.animal / self.session_id

    def task(self, name: str) -> Task:
        for t in self.tasks:
            if t.name == name:
                return t
        raise ConfigError(
            f"Task {name!r} is not listed in {self.path.name}. "
            f"Known tasks: {[t.name for t in self.tasks]}"
        )

    def task_dir(self, name: str) -> Path:
        return self.session_dir / self.task(name).name

    def raw_dir(self, task: str) -> Path:
        return self.task_dir(task) / "raw"

    def processed_dir(self, task: str) -> Path:
        return self.task_dir(task) / "processed"

    def derivatives_dir(self, task: str) -> Path:
        return self.task_dir(task) / "derivatives"

    # --- step settings -------------------------------------------------------
    def step(self, name: str) -> dict[str, Any]:
        """Settings for one pipeline step, with paths resolved.

        Keys ending in ``_dir``, ``_file`` or ``_path`` are paths. Absolute paths are
        used as written; relative paths are resolved against the step's task folder
        (if the section sets ``task = "..."``) or else the session folder.
        """
        if name not in self.steps:
            raise ConfigError(f"{self.path.name} has no [{name}] section.")
        raw = dict(self.steps[name])
        task = raw.get("task")
        out: dict[str, Any] = {}
        for key, value in raw.items():
            if key.endswith(PATH_SUFFIXES) and isinstance(value, str):
                out[key] = self.resolve(value, task=task)
            else:
                out[key] = value
        return out

    def resolve(self, value: str, base: Path | None = None, task: str | None = None) -> Path:
        """Absolute paths as written; relative ones inside ``base``, the task folder
        or the session folder (in that order). Only relative paths need data_root."""
        p = Path(value).expanduser()
        if p.is_absolute() or re.match(r"^[A-Za-z]:[\\/]", value):
            return p
        if base is None:
            base = self.task_dir(task) if task else self.session_dir
        return base / p

    def summary(self) -> str:
        lines = [
            f"config      : {self.path}",
            f"session_id  : {self.session_id}",
            f"probe       : {self.probe}",
            f"data_root   : {self.data_root or '(not set)'}",
        ]
        if self.data_root is not None:
            lines.append(f"session_dir : {self.session_dir}")
            for t in self.tasks:
                lines.append(f"  task {t.name:<10}: {self.task_dir(t.name)}")
        lines.append(f"steps       : {', '.join(self.steps) or '(none)'}")
        return "\n".join(lines)


# -----------------------------------------------------------------------------
def load_local() -> dict[str, Any]:
    """Machine-specific settings from configs/local.toml + environment variables."""
    local: dict[str, Any] = {}
    if LOCAL_CONFIG.exists():
        with open(LOCAL_CONFIG, "rb") as f:
            local = tomllib.load(f)
    if os.environ.get("CCLAB_DATA_ROOT"):
        local["data_root"] = os.environ["CCLAB_DATA_ROOT"]
    if os.environ.get("CCLAB_CATGT"):
        local["catgt_path"] = os.environ["CCLAB_CATGT"]
    return local


def find_config(path: str | os.PathLike) -> Path:
    """Accept a path relative to the current folder *or* to the repo root.

    Notebooks run from ``notebooks/``, so ``"configs/npx/x.toml"`` should still work.
    """
    p = Path(path).expanduser()
    for candidate in (p, REPO_ROOT / p):
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError(f"Config file not found: {path} (also looked in {REPO_ROOT})")


def load_config(path: str | os.PathLike, data_root: str | os.PathLike | None = None) -> Config:
    """Load and validate a session config.

    ``data_root`` overrides configs/local.toml and $CCLAB_DATA_ROOT.
    """
    cfg_path = find_config(path)
    text = cfg_path.read_text()
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"{cfg_path.name}: invalid TOML: {e}") from e

    local = load_local()
    if data_root is not None:
        local["data_root"] = str(data_root)

    session = data.pop("session", None)
    if session is None:
        raise ConfigError(f"{cfg_path.name}: missing [session] section.")
    for key in ("animal", "date", "area", "probe"):
        if key not in session:
            raise ConfigError(f"{cfg_path.name}: [session] is missing {key!r}.")

    animal = str(session["animal"])
    area = str(session["area"])
    probe = str(session["probe"])
    date = _normalize_date(str(session["date"]), cfg_path.name)
    _check_vocab(animal, ANIMALS, "animal", cfg_path.name)
    _check_vocab(area, AREAS, "area", cfg_path.name)
    _check_vocab(probe, set(PROBE_FOLDERS), "probe", cfg_path.name)

    tasks = []
    for t in data.pop("tasks", []):
        t = dict(t)
        if "name" not in t:
            raise ConfigError(f"{cfg_path.name}: every [[tasks]] entry needs a name.")
        _warn_unknown_task(t["name"], cfg_path.name)
        tasks.append(
            Task(
                name=t.pop("name"),
                spikeglx_run=t.pop("spikeglx_run", None),
                gate=int(t.pop("gate", 0)),
                extra=t,
            )
        )
    if not tasks:
        raise ConfigError(f"{cfg_path.name}: list at least one [[tasks]] block.")

    steps = {k: v for k, v in data.items() if isinstance(v, dict)}
    root = local.get("data_root")
    cfg = Config(
        path=cfg_path,
        text=text,
        animal=animal,
        date=date,
        area=area,
        probe=probe,
        tasks=tasks,
        session=session,
        steps=steps,
        data_root=Path(root).expanduser() if root else None,
        local=local,
    )
    for name, sec in steps.items():
        if "task" in sec:
            cfg.task(sec["task"])  # raises a clear error for typos
    return cfg


def _normalize_date(value: str, fname: str) -> str:
    digits = value.replace("-", "")
    try:
        if not re.fullmatch(r"(19|20)\d{6}", digits):
            raise ValueError
        _dt.datetime.strptime(digits, "%Y%m%d")
    except ValueError:
        raise ConfigError(
            f"{fname}: date {value!r} must be YYYYMMDD or YYYY-MM-DD "
            "(the lab standard switched away from MMDDYY)."
        ) from None
    return digits


def _check_vocab(value: str, allowed: set[str], what: str, fname: str) -> None:
    if value not in allowed:
        raise ConfigError(
            f"{fname}: unknown {what} {value!r}. Allowed: {sorted(allowed)}. "
            "If this is a new value, add it to src/cclab_preproc/config.py."
        )


def _warn_unknown_task(name: str, fname: str) -> None:
    base = re.sub(r"\d+$", "", name.removesuffix("+stim"))
    if base not in TASKS:
        warnings.warn(
            f"{fname}: task {name!r} is not in the controlled vocabulary {sorted(TASKS)}.",
            stacklevel=3,
        )
