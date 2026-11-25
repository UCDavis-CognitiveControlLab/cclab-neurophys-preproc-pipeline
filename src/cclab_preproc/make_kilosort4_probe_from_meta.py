"""
Build a Kilosort4 probe/channel map from a SpikeGLX .ap.meta file.

Works for whatever electrode configuration was actually recorded (different
banks, channel subsets, NP2.0 multi-shank, ...), because the geometry is read
from the meta file rather than assumed to be the standard 384-site layout.

Geometry source, in order of preference:
  1. ~snsGeomMap  (SpikeGLX >= 20230202): explicit shank / x / y per channel
  2. ~snsShankMap (older SpikeGLX): shank / col / row per channel, converted
     to um using the known geometry of the probe type

Usage
-----
    python make_kilosort4_probe_from_meta.py path/to/run_g0_t0.imec0.ap.meta
    python make_kilosort4_probe_from_meta.py path/to/run.ap.meta -o probe.json --plot

In Python
---------
    from make_kilosort4_probe_from_meta import probe_from_meta
    probe = probe_from_meta('run_g0_t0.imec0.ap.meta')
    run_kilosort(settings=settings, probe=probe)   # or probe_name='probe.json'
"""
import argparse
import json
import re
from pathlib import Path

import numpy as np


def read_meta(meta_path):
    """Parse a SpikeGLX .meta file into a dict of strings (keys keep any '~')."""
    meta = {}
    with open(meta_path, 'r') as f:
        for line in f:
            if '=' in line:
                k, v = line.rstrip('\r\n').split('=', 1)
                meta[k.strip()] = v.strip()
    return meta


def _groups(s):
    """'(a:b)(c:d)' -> [['a','b'], ['c','d']] ; header groups split on ','."""
    return re.findall(r'\(([^)]*)\)', s)


def _saved_ap_channels(meta):
    """Indices (into the acquired channel list) of AP channels in the .bin."""
    n_ap = int(meta['snsApLfSy'].split(',')[0])
    subset = meta.get('snsSaveChanSubset', 'all').strip()
    if subset in ('all', ''):
        saved = np.arange(int(meta['nSavedChans']))
    else:
        saved = []
        for part in subset.split(','):
            if ':' in part:
                a, b = (int(x) for x in part.split(':'))
                saved.extend(range(a, b + 1))
            else:
                saved.append(int(part))
        saved = np.asarray(saved)
    return saved[saved < n_ap], n_ap


def _geometry_from_geom_map(meta, n_ap):
    g = _groups(meta['~snsGeomMap'])
    header, entries = g[0].split(','), g[1:]
    shank_spacing = float(header[2])
    shank, x, y = [], [], []
    for e in entries:
        s, xx, yy, _used = e.split(':')
        shank.append(int(s))
        x.append(float(xx) + int(s) * shank_spacing)
        y.append(float(yy))
    return np.array(shank), np.array(x), np.array(y)


def _geometry_from_shank_map(meta):
    """Older files: (shank:col:row:used) -> um using probe-type geometry."""
    g = _groups(meta['~snsShankMap'])
    n_shank, n_col, n_row = (int(v) for v in g[0].split(','))
    prb = int(meta.get('imDatPrb_type', 0))
    if prb in (21, 2003, 2004, 24, 2013, 2014):          # NP2.0 family
        col_pitch, row_pitch, shank_spacing = 32.0, 15.0, 250.0
        stagger = lambda row: 0.0
        x0 = 0.0
    else:                                                # NP1.0 family
        col_pitch, row_pitch, shank_spacing = 32.0, 20.0, 0.0
        # NP1.0 is staggered: even rows start at 27 um, odd rows at 11 um
        stagger = lambda row: 27.0 if row % 2 == 0 else 11.0
        x0 = 0.0
    shank, x, y = [], [], []
    for e in g[1:]:
        s, c, r, _used = (int(v) for v in e.split(':'))
        shank.append(s)
        x.append(x0 + s * shank_spacing + c * col_pitch + stagger(r))
        y.append(r * row_pitch)
    return np.array(shank), np.array(x), np.array(y)


def probe_from_meta(meta_path, exclude_channels=None):
    """
    Return a Kilosort4 probe dict built from a SpikeGLX .meta file.

    chanMap indexes columns of the .bin (0-based, sync channel excluded),
    n_chan is the number of channels *used for sorting*. Kilosort's
    n_chan_bin (total columns in the .bin, incl. sync) is nSavedChans in the
    meta file and is set in the settings, not the probe.

    exclude_channels : optional iterable of .bin channel indices to drop
        (bad channels), so Kilosort ignores them.
    """
    meta = read_meta(meta_path)
    saved_ap, n_ap = _saved_ap_channels(meta)

    if '~snsGeomMap' in meta:
        shank, x, y = _geometry_from_geom_map(meta, n_ap)
    elif '~snsShankMap' in meta:
        shank, x, y = _geometry_from_shank_map(meta)
    else:
        raise ValueError('Meta has neither ~snsGeomMap nor ~snsShankMap; '
                         'is this an imec .ap.meta file?')

    # geometry entries are indexed by acquired channel; the .bin holds saved_ap
    if len(x) < saved_ap.max() + 1:
        raise ValueError(f'Geometry has {len(x)} entries but meta saves channel '
                         f'{saved_ap.max()}')
    x, y, shank = x[saved_ap], y[saved_ap], shank[saved_ap]
    chan_map = np.arange(len(saved_ap))          # column positions in the .bin

    keep = np.ones(len(chan_map), bool)
    if exclude_channels is not None:
        keep[np.isin(chan_map, list(exclude_channels))] = False

    probe = {
        'chanMap': chan_map[keep].astype(np.int32),
        'xc': x[keep].astype(np.float32),
        'yc': y[keep].astype(np.float32),
        'kcoords': shank[keep].astype(np.float32),
        'n_chan': int(keep.sum()),
    }
    probe['_n_chan_bin'] = int(meta['nSavedChans'])   # informational only
    return probe


def save_probe_json(probe, path):
    """Write in the same layout as kilosort.io.save_probe (loadable by load_probe)."""
    out = {k: (v.tolist() if isinstance(v, np.ndarray) else v)
           for k, v in probe.items() if not k.startswith('_')}
    with open(path, 'w') as f:
        json.dump(out, f, indent=2)


def save_probe_mat(probe, path):
    """
    Write a Kilosort2/3-style channel map .mat (also read by kilosort4's
    load_probe, which uses chanMap [1-based], xcoords, ycoords, kcoords,
    connected). Needs scipy.
    """
    from scipy.io import savemat
    n = len(probe['chanMap'])
    savemat(path, {
        'chanMap': (probe['chanMap'] + 1).astype(np.float64).reshape(-1, 1),  # MATLAB 1-based
        'chanMap0ind': probe['chanMap'].astype(np.float64).reshape(-1, 1),
        'xcoords': probe['xc'].astype(np.float64).reshape(-1, 1),
        'ycoords': probe['yc'].astype(np.float64).reshape(-1, 1),
        'kcoords': probe['kcoords'].astype(np.float64).reshape(-1, 1),
        'connected': np.ones((n, 1), dtype=bool),
        'name': Path(path).stem,
    })


def save_probe(probe, path):
    """Save as .json or .mat depending on the extension of `path`."""
    suffix = Path(path).suffix.lower()
    if suffix == '.json':
        save_probe_json(probe, path)
    elif suffix == '.mat':
        save_probe_mat(probe, path)
    else:
        raise ValueError('output must end in .json or .mat')


def plot_probe(probe):
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(3, 8))
    sc = ax.scatter(probe['xc'], probe['yc'], c=probe['kcoords'], s=12, cmap='tab10')
    ax.set_xlabel('x (um)'); ax.set_ylabel('y (um from tip)')
    ax.set_title(f"{probe['n_chan']} channels")
    ax.set_aspect('equal')
    plt.tight_layout(); plt.show()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('meta', help='path to the .ap.meta file')
    ap.add_argument('-o', '--out', help='output file, .json or .mat '
                    '(default: writes both <meta stem>_ks4_probe.json and .mat)')
    ap.add_argument('--exclude', type=int, nargs='*', default=None,
                    help='bin channel indices to exclude (bad channels)')
    ap.add_argument('--plot', action='store_true')
    a = ap.parse_args()

    probe = probe_from_meta(a.meta, exclude_channels=a.exclude)
    if a.out:
        outs = [Path(a.out)]
    else:
        # plain string concat: with_suffix would clobber dotted names like run.imec0.ap
        stem = Path(a.meta).with_suffix('').name
        outs = [Path(a.meta).with_name(f'{stem}_ks4_probe{ext}')
                for ext in ('.json', '.mat')]
    for out in outs:
        save_probe(probe, out)
        print(f"wrote {out}")
    print(f"  channels used : {probe['n_chan']}")
    print(f"  n_chan_bin    : {probe['_n_chan_bin']}  (set in Kilosort settings)")
    print(f"  shanks        : {sorted(set(int(k) for k in probe['kcoords']))}")
    print(f"  x range       : {probe['xc'].min():.0f}-{probe['xc'].max():.0f} um")
    print(f"  y range       : {probe['yc'].min():.0f}-{probe['yc'].max():.0f} um")
    if a.plot:
        plot_probe(probe)


if __name__ == '__main__':
    main()
