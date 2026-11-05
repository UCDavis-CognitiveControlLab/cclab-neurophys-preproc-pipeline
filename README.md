# cclab-neurophys-preproc-pipeline

Preprocessing for the UC Davis Cognitive Control Lab's high-density recordings: from raw SpikeGLX data to
spike-sorted, curated units packed into the lab's grab-and-go `<task>.mat` metafile.

```
raw SpikeGLX ──► CatGT pass 1 ──► supercat ──► Kilosort 4 ──► Phy curation ──► <task>.mat metafile
               (filter, CAR,      (join task    (sorting)      (manual)          (spikes + trials +
                artifacts, edges)  blocks)                                        events, one file)
   step 1            1                1             2              3                    4
```

Everything that differs between recordings lives in **one config file per session**
(`configs/<probe>/<session_id>.toml`), so no code or notebook has to be edited to process a new session, and the
config is archived next to every output it produced. Folder layout and names follow the
[CC Lab Data Organization Standard](docs/data-standard.md).

## Quick start

1. **Install [uv](https://docs.astral.sh/uv/getting-started/installation/)** (one time):
   - macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Windows (PowerShell): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
2. **Get the code and install** (uv downloads the right Python by itself):
   ```bash
   git clone git@github.com:UCDavis-CognitiveControlLab/cclab-neurophys-preproc-pipeline.git
   cd cclab-neurophys-preproc-pipeline
   uv sync
   ```
3. **Tell it where the data are on this computer**: copy `configs/local.example.toml` to `configs/local.toml` and
   set `data_root` (the lab share) and `catgt_path`. This file is not committed.
4. **Try it on synthetic data** (no real data needed):
   ```bash
   uv run cclab-preproc make-demo demo_data
   uv run cclab-preproc show demo_data/venni_20250731_SEF.toml --data-root demo_data
   uv run cclab-preproc build-meta demo_data/venni_20250731_SEF.toml --data-root demo_data
   ```

## Processing a session

```bash
uv run cclab-preproc new-config                  # asks for animal, date, area, probe, task blocks
uv run cclab-preproc show configs/npx/venni_20250731_SEF.toml    # where every step reads/writes
uv run cclab-preproc catgt configs/npx/venni_20250731_SEF.toml   # prints the CatGT commands
uv run cclab-preproc catgt configs/npx/venni_20250731_SEF.toml --run
#   → run Kilosort 4 on the folder `show` prints, then curate in Phy (docs/pipeline.md)
uv run cclab-preproc build-meta configs/npx/venni_20250731_SEF.toml
```

Commit the session config when you're done: the configs folder is the lab's record of how each session was
processed. Step-by-step details, including Kilosort and Phy: **[docs/pipeline.md](docs/pipeline.md)**.

## Notebooks

Open with `uv run jupyter lab`. Each notebook starts with a **settings cell** where you choose the session config;
nothing further down needs editing.

| notebook | what it does | config section |
|---|---|---|
| `Build_Recording_Meta.ipynb` | builds `<task>.mat` after Phy curation, with a PSTH sanity check | `[meta]` |
| `Neuropix_Processing_MI_Timescale.ipynb` | MI-based visual / memory / motor classification, Neuropixels MGS with distractors | `[mi_classification]` |
| `Ripple_Processing_MI_Timescale.ipynb` | same for 32-channel Ripple data | `[mi_classification]` |

The two MI notebooks come from `CCLab-BrindaRepo/HighDensity data processing`; see
[docs/known-issues.md](docs/known-issues.md) before relying on their results.

## Repository layout

```
configs/
  local.example.toml        copy to local.toml: data_root, catgt_path (per machine)
  _template.toml            what new-config fills in; documents every option
  <probe>/<session_id>.toml one per recording session (probe = npx | sprobe | ripple)
notebooks/                  Jupyter notebooks (settings cell at the top)
src/cclab_preproc/          the Python package behind the CLI and notebooks
matlab/BuildRecordingMeta.m MATLAB version of the metafile builder
scripts/catgt/*.bat         original CatGT .bat files (superseded by `cclab-preproc catgt`)
docs/                       pipeline, configuration, data standard, known issues
tests/                      `uv run pytest` (also runs every notebook on synthetic data)
```

## Docs

- [docs/pipeline.md](docs/pipeline.md): the steps, from raw data to metafile
- [docs/configuration.md](docs/configuration.md): config file reference, paths, archiving
- [docs/data-standard.md](docs/data-standard.md): how this repo applies the CC Lab Data Organization Standard
- [docs/known-issues.md](docs/known-issues.md): open questions and analysis caveats

## Development

```bash
uv run pytest                       # all tests (~30 s)
uv run pytest -m "not notebooks"    # skip executing notebooks
uv add <package>                    # add a dependency (updates pyproject.toml + uv.lock; commit both)
```

Clear notebook outputs before committing (*Edit > Clear Outputs of All Cells*): outputs can contain data and make diffs unreadable.
