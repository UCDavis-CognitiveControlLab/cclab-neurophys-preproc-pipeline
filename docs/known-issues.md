# Known issues and open questions

## Pipeline gaps

### Supercat and the metafile
With supercat, Kilosort sorts all task blocks as one continuous recording, so `spike_times.npy` is on the
**supercat timeline**. Each task block's `sync_event_codes.npy` is on that block's own clock. To build a per-task
`<task>.mat` from a supercat sort, spike times have to be shifted by the block's start offset (CatGT records the
offsets in the supercat output; see the *supercat* section of the CatGT ReadMe) and clipped to the block.
`build-meta` and `BuildRecordingMeta.m` don't do this yet. Until they do, use them only on sorts of a single task
block, or check the alignment by hand.

### Event codes (`processed/events/sync_event_codes.npy`)
Both metafile builders expect this file, but the code that makes it from the NI edge files isn't in this repo.
It, and `GainCorrectIM`, seem to come from the lab's `ks4_pipeline-main` / `neuropixel_preprocessing_module`
(imported by `CCLab-BrindaRepo/Script_dlPFC/getNeuropixelData_dLPFC_Paper.ipynb`). That module should be added
here as a step between CatGT and build-meta.

### Other
- `sessions.csv` isn't read or updated by the pipeline yet.
- Behavioral files saved as MATLAB `table` objects can only be read by `matlab/BuildRecordingMeta.m`.
- Ripple acquisition import (`RippleDAQ.m`, `getRipple_MGS.m`) hasn't been brought in yet.
- LFP isn't in the metafile yet (`meta.lfp.status = "not_yet_added"`), same as the MATLAB builder.

## Fixed in this repo (see git history)

- Neuropixels notebook: the 45°/180° PSTHs were used but never loaded, and the combined MI tests paired 0°-only
  PSTHs with labels for all trials, so the notebook couldn't run.
- Neuropixels notebook: per-distractor 0° results were unpacked from `results_45` (visual, memory and motor sections).
- `BuildRecordingMeta.m`: `cfg.builder_version` was read but never set.

## MI notebooks: analysis caveats (not changed)

These affect results, so the analysis owner should decide on them. Cell references are to the current notebooks.

**Both notebooks**
1. **Motor / post-saccade rate filter uses the wrong alignment.** After the MI tests, the "mean rate above
   `min_rate`" filter takes `motor_window` / `post_saccade_window` bins (saccade-aligned) from `psth_combined`
   (target-aligned). It should probably use `align_psth_combined`.
2. **No fixed random seed.** Permutations use the global NumPy RNG inside joblib workers, and
   `mutual_info_classif` has no `random_state` in `neuron_mi_perm` / `mi_diff_permutation_test`, so p-values
   change slightly between runs.
3. **`mi_diff_permutation_test`** is commented "one-tailed" but compares `|diff|` (two-tailed), and shuffles the
   labels independently for the two epochs.
4. **No multiple-comparison correction** across neurons (the Ripple notebook computes FDR with `multipletests`
   but doesn't use it).
5. Window comments in the original code didn't match the bins (e.g. baseline `slice(0, 50)` was labelled
   "0ms to 300ms" but is -500 to 0 ms). The configs now give the correct ms values.

**Neuropixels notebook**
6. **Swapped column names** in `results_MI_Timescale`: `mi_mem_*` and `mi_mt_*` hold the *vs-baseline
   difference* and `mi_mem_comp_*` / `mi_mt_comp_*` hold the *epoch-only* MI, the opposite of the visual columns
   (`mi_v_*` = epoch-only, `mi_vcomp_*` = difference).
7. Combined tests assume trials are ordered 0°, 45°, 180°; there's now an `assert` for this.
8. Motor PSTH figures are saved as `VNeuron_*.png`.

**Ripple notebook**
9. Neurons are classified by the epoch-responsiveness test (`mi_responsiveness_test`, baseline vs epoch) alone.
   The Neuropixels notebook uses direction selectivity (`neuron_mi_perm` OR `mi_diff_permutation_test`), so
   "visual neuron" means different things on the two rigs.
10. Z-scoring leaves the first and last 10 bins at 0. Plot y-limits use `max(np.min(...))` where `min` was
    probably intended.

**Disabled cells**: both notebooks contain old code saved as *markdown* cells (tuning curves, K-S tests, timescale
plots). They still have hardcoded `D:\` paths and use variables that are never defined
(`visual_neurons_mi45`, `visual_neurons_idx`). They're left as they were.
