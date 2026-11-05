"""Command line: ``uv run cclab-preproc <command> ...`` (``--help`` on any command)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import ANIMALS, AREAS, PROBE_FOLDERS, REPO_ROOT, ConfigError, load_config


def cmd_new_config(a: argparse.Namespace) -> None:
    def ask(prompt: str, value: str | None, choices=None) -> str:
        if value:
            return value
        hint = f" ({'/'.join(sorted(choices))})" if choices else ""
        return input(f"{prompt}{hint}: ").strip()

    animal = ask("animal", a.animal, ANIMALS)
    date = ask("date YYYYMMDD", a.date).replace("-", "")
    area = ask("area", a.area, AREAS)
    probe = ask("probe", a.probe, PROBE_FOLDERS)
    tasks = a.task or [
        t.strip() for t in ask("task blocks as name:SpikeGLXrun, comma separated (e.g. mgs:MGS1,FV:FV1)", None).split(",")
        if t.strip()
    ]
    blocks, first = [], None
    for t in tasks:
        name, _, run = t.partition(":")
        first = first or name
        blocks.append(f'[[tasks]]\nname = "{name}"\nspikeglx_run = "{run or name.upper()}"\ngate = 0\n')

    template = (REPO_ROOT / "configs" / "_template.toml").read_text()
    text = (
        template.replace("{animal}", animal).replace("{date}", date).replace("{area}", area)
        .replace("{probe}", probe).replace("{tasks}", "\n".join(blocks)).replace("{first_task}", first or "")
    )
    out = REPO_ROOT / "configs" / probe / f"{animal}_{date}_{area}.toml"
    if out.exists() and not a.force:
        sys.exit(f"{out} already exists (use --force to overwrite).")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    load_config(out)  # validate
    print(f"Wrote {out.relative_to(REPO_ROOT)}. Review it, then: uv run cclab-preproc show {out.relative_to(REPO_ROOT)}")


def cmd_show(a: argparse.Namespace) -> None:
    from . import catgt

    cfg = load_config(a.config, data_root=a.data_root)
    print(cfg.summary())
    if cfg.data_root is None:
        return
    print("\nStep 1  CatGT:")
    for c in catgt.all_commands(cfg):
        print(f"  {c.label:<16} -> {c.dest}")
    print(f"\nStep 2  Kilosort input folder (*.ap.bin):\n  {catgt.kilosort_input(cfg)}")
    if "meta" in cfg.steps:
        from .meta import settings

        s = settings(cfg)
        print("\nStep 4  build-meta:")
        for k in ("ks_dir", "sync_events_file", "behavior_file", "out_file"):
            p = s[k]
            mark = "" if p is None else ("ok" if Path(p).exists() else "MISSING")
            print(f"  {k:<17} {p or '(none)'}  {mark}")


def cmd_catgt(a: argparse.Namespace) -> None:
    from . import catgt

    catgt.run(load_config(a.config, data_root=a.data_root), execute=a.run, only=a.only)


def cmd_build_meta(a: argparse.Namespace) -> None:
    from . import meta

    meta.build(load_config(a.config, data_root=a.data_root))


def cmd_make_demo(a: argparse.Namespace) -> None:
    from .demo import make_demo

    root = Path(a.dir).resolve()
    cfg = make_demo(root)
    print(f"Demo data written to {root}\nTry:\n"
          f"  uv run cclab-preproc show {cfg} --data-root {root}\n"
          f"  uv run cclab-preproc build-meta {cfg} --data-root {root}")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="cclab-preproc", description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    def with_config(sp):
        sp.add_argument("config", help="session config, e.g. configs/npx/venni_20250731_SEF.toml")
        sp.add_argument("--data-root", help="override data_root from configs/local.toml")
        return sp

    sp = sub.add_parser("new-config", help="create configs/<probe>/<session_id>.toml from the template")
    sp.add_argument("--animal")
    sp.add_argument("--date", help="YYYYMMDD")
    sp.add_argument("--area")
    sp.add_argument("--probe")
    sp.add_argument("--task", action="append", help="name:SpikeGLXrun, repeat per task block (e.g. --task mgs:MGS1)")
    sp.add_argument("--force", action="store_true")
    sp.set_defaults(func=cmd_new_config)

    with_config(sub.add_parser("show", help="print resolved paths for every step")).set_defaults(func=cmd_show)

    sp = with_config(sub.add_parser("catgt", help="CatGT pass 1 + supercat (dry run unless --run)"))
    sp.add_argument("--run", action="store_true", help="actually run CatGT")
    sp.add_argument("--only", choices=["pass1", "supercat"])
    sp.set_defaults(func=cmd_catgt)

    with_config(sub.add_parser("build-meta", help="build the <task>.mat metafile")).set_defaults(func=cmd_build_meta)

    sp = sub.add_parser("make-demo", help="write a small synthetic session to try the pipeline")
    sp.add_argument("dir", nargs="?", default="demo_data")
    sp.set_defaults(func=cmd_make_demo)

    a = p.parse_args(argv)
    try:
        a.func(a)
    except (ConfigError, FileNotFoundError) as e:
        sys.exit(f"error: {e}")


if __name__ == "__main__":
    main()
