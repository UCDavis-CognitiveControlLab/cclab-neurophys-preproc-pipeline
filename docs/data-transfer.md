# Getting recordings onto the sorting PC

Written 2026-11-23 for the lab sorting PC (`cns-ddhn7qkm3`, Windows). Sort from a local copy, never straight off
the NAS: one 94-minute recording took 13 h to sort when read over the network.

## Drives on this PC

| Drive | What it is | Use it for |
|---|---|---|
| `R:` | The NAS (`\\cns-nas.ucdavis.edu\cclab`), the lab's live data | Source of raw recordings; final home of results |
| `D:` "SORTING" | Internal 4 TB disk, one folder per person | Local working copies and sorting (1.7 TB free on 2026-11-23) |
| `G:` "CCLABDATA" | External 11 TB USB drive | Archive copy of older lab data. Not a workspace |
| `C:` | System disk, 140 GB free | Not for data |

`R:` exists only on the Windows side. WSL cannot see it, and WSL reaches `D:` through a slow bridge, so copy from
Windows PowerShell.

## Where a local copy goes

`D:\<your name>\data\` in the lab data-standard layout:

```
D:\<you>\data\neuropixel\<animal>\<animal>_<YYYYMMDD>_<area>\<task>\raw\
```

## Copy with robocopy (PowerShell)

Example: the 2026-10-10 movie recording.

```powershell
robocopy "R:\shared\current\Neuropixel\101026_V_SEF_ACC\Movie" `
         "D:\Quincy\data\neuropixel\venni\venni_20261010_SEF\movie\raw" `
         /E /R:5 /W:15 /XF *.lf.bin /TEE /LOG:D:\Quincy\copy_101026.log
```

| Flag | Meaning |
|---|---|
| `/E` | include subfolders |
| `/R:5 /W:15` | on an error, retry 5 times, 15 s apart (the default is a million retries) |
| `/XF *.lf.bin` | skip the low-frequency file; sorting does not need it |
| `/TEE /LOG:<file>` | show progress and also save it to a log |

- Safe to re-run: files already copied are skipped. A file that was interrupted part-way starts over.
- **Do not use `/Z`** (restartable mode). Measured here it cut the copy from 11 MB/s to 2 MB/s, because it
  forces many small flushed writes to the hard disk.
- Define any `$variables` in the same PowerShell window before the `robocopy` lines. With an empty variable
  robocopy silently looks under `C:\` and reports "cannot find the path".
- **Never add `/MIR` or `/PURGE`.** They delete files at the destination that are missing from the source.
- Not drag and drop (no resume on a 50 GB file, no log). Not rsync (WSL cannot see `R:`).

## How long

Measured from this PC on 2026-11-23: about 11 MB/s reading from the NAS, so roughly 25 minutes per 15 GB. The
10-10 movie (51 GB without the `lf.bin`) takes about 80 minutes.

The limit is the network path, not this PC: the adapter links at 1 Gbps, `D:` writes at about 120 MB/s, and three
simultaneous reads from the NAS still total about 12 MB/s. That is what a 100 Mbit hop (or a server-side limit)
looks like, so copying sessions in parallel does not help. Worth asking IT about.

## Check the copy

The `.meta` file next to each `.bin` records the size the recording should be:

```powershell
$d = "D:\Quincy\data\neuropixel\venni\venni_20261010_SEF\movie\raw\Movie_g0\Movie_g0_imec0"
Select-String -Path "$d\*.ap.meta" -Pattern '^fileSizeBytes'
(Get-Item "$d\*.ap.bin").Length
```

The two numbers must match. The robocopy log should end with `0` in the FAILED column.

## Sending results back

Copy only the sort output folder to the session's folder on `R:`, with the same flags and without `/XF`. Raw data
on the NAS is never overwritten or deleted from here.
