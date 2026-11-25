# %% First block

from pathlib import Path
from tkinter.constants import FALSE

run = Path("/mnt/d/Quincy/data/neuropixel/venni/venni_20261010_SEF/movie/raw/Movie_g0")

list((run / "Movie_g0_imec0").iterdir())
meta_path = run / "Movie_g0_imec0" / "Movie_g0_t0.imec0.ap.meta"

text = meta_path.read_text()
print(text[:2000])
# %% 2

meta = dict(line.split('=', 1) for line in text.splitlines() if "=" in line)

# for key in meta:
#     if meta[key].__sizeof__() < 1000:
#         print(key, "=", meta[key])

for key in ["imSampRate", "nSavedChans", "fileSizeBytes", "fileTimeSecs"]:
    print(key, '=', meta[key])
# %% 3
BYTES_PER_INT_PER_CHANNEL = 2

predictedSize = BYTES_PER_INT_PER_CHANNEL * float(meta["imSampRate"]) * float(meta["nSavedChans"]) * float(meta["fileTimeSecs"])

print(predictedSize)
print(meta['fileSizeBytes'])
# %% 4
import numpy as np

bin_path = meta_path.with_suffix(".bin")
n_ch = int(meta["nSavedChans"])
data = np.memmap(bin_path, dtype=np.int16, mode="r").reshape(-1, n_ch)
print(data.shape)
print(data[0:100, 10])



# %% 5 visualize raw signal

import matplotlib.pyplot as plt
# Ai = analoug input
aiRangeMax, maxInt, gain = (float(meta[k]) for k in ["imAiRangeMax", "imMaxInt", "imChan0apGain"])

# imChan0apGain=500
# imAiRangeMax=0.6
# imMaxInt
# # imAiRangeMax=0.6
# why 1,000,000?
CHAN_RANGE = (100, 128)
START_SECS = 0
CLIP_LEN_SECS = 0.1

samp_rate = float(meta["imSampRate"])
start = int(START_SECS * samp_rate)
chunk = data[start : start + int(CLIP_LEN_SECS * samp_rate), CHAN_RANGE[0]:CHAN_RANGE[1]].astype(float)
chunk -= np.median(chunk, axis=0) #  center
# uv = chunk * 0.6 / 512 / 500 * 1e6 # where are these values coming from?

micro_volts = chunk * aiRangeMax / maxInt / gain * 1e6
t = np.arange(len(micro_volts )) / samp_rate * 1000


SPACING = 150
PLT_SIZE = (20, 16)
DPI = 120
n = micro_volts.shape[1]

fig, ax = plt.subplots(figsize=(PLT_SIZE[0],PLT_SIZE[1]), dpi=DPI)
for i in range(n):
    ax.plot(t, micro_volts[:,i]+i* SPACING, lw=0.25)

ax.set_yticks(np.arange(n) * SPACING, range(CHAN_RANGE[0], CHAN_RANGE[1]))
ax.set_xlabel("ms")
ax.set_ylabel("channel (offset 150 $\mu V$ each)")

ax.plot([t[-1] * 1.01] * 2, [0, 100], color="r", lw=3, clip_on=False)
ax.text(t[-1] * 1.02, 50, r"$100 \mu V$", color="r", va="center")
