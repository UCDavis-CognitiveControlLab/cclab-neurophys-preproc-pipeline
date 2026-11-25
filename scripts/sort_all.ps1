# Sort every SpikeGLX recording under a data folder with Kilosort 4, one after another.
#
#   powershell -ExecutionPolicy Bypass -File scripts\sort_all.ps1            # sort everything not yet sorted
#   powershell -ExecutionPolicy Bypass -File scripts\sort_all.ps1 -List      # only show what would run
#   powershell -ExecutionPolicy Bypass -File scripts\sort_all.ps1 -Logout    # sign out of Windows after the last sort
#   powershell -ExecutionPolicy Bypass -File scripts\sort_all.ps1 -Shutdown  # power off 5 minutes after the last sort
#
# Finds <DataRoot>\*\<Task>\raw\<run>\<run>_imecN\*.ap.bin, smallest first. Results go to
# <session>\<Task>\processed\kilosort4 (one probe) or kilosort4_imecN (several probes).
# A recording whose results folder already has spike_times.npy is skipped, so the script can be
# re-run after an interruption. A failed sort is recorded and the next one still runs.
# One line per recording is appended to <DataRoot>\sort_all.log; Kilosort's own log is in each
# results folder. Run it in WezTerm or Windows Terminal: a click in a classic PowerShell window
# pauses the job.
param(
    [string]$DataRoot = "D:\Quincy\data\neuropixel\venni",
    [string]$Task = "movie",
    [string]$Venv = "D:\Quincy\venvs\cclab-preproc",   # Windows environment made by `uv sync --extra sort`
    [string]$ResultsName = "kilosort4",
    [double]$TmaxSeconds = 0,                            # > 0: sort only the first N seconds (testing)
    [switch]$DropFlagged,                                # leave out channels SpikeGLX marks unused (default keeps them)
    [switch]$List,
    [switch]$Logout,                                     # sign out when finished (closes everything you have open)
    [switch]$Shutdown
)

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo
$env:UV_PROJECT_ENVIRONMENT = $Venv
$log = Join-Path $DataRoot "sort_all.log"

$bins = @(Get-ChildItem -Path (Join-Path $DataRoot "*\$Task\raw\*\*_imec*\*.ap.bin") -ErrorAction SilentlyContinue |
    Sort-Object Length)
if ($bins.Count -eq 0) { Write-Host "error: no ap.bin found under $DataRoot\*\$Task\raw"; exit 1 }

$jobs = foreach ($bin in $bins) {
    $probeDir = $bin.Directory                       # ...\raw\<run>\<run>_imecN
    $taskDir = $probeDir.Parent.Parent.Parent        # ...\<session>\<Task>
    $nProbes = @(Get-ChildItem -Directory -Path $probeDir.Parent.FullName -Filter "*_imec*").Count
    $name = $ResultsName
    if ($nProbes -gt 1) { $name = "$ResultsName" + "_" + ($probeDir.Name -replace '^.*_(imec\d+)$', '$1') }
    $results = Join-Path $taskDir.FullName "processed\$name"
    [pscustomobject]@{
        Bin     = $bin.FullName
        GB      = [math]::Round($bin.Length / 1GB, 1)
        Results = $results
        Done    = Test-Path (Join-Path $results "spike_times.npy")
    }
}

$jobs | Format-Table -AutoSize -Wrap GB, Done, Bin, Results | Out-String -Width 250 | Write-Host
if ($List) { exit 0 }

$failed = 0
foreach ($j in $jobs) {
    if ($j.Done) { Add-Content $log "$(Get-Date -Format s)  SKIP (already sorted)  $($j.Results)"; continue }
    $sortArgs = @("run", "--extra", "sort", "python", "-m", "cclab_preproc.sort", $j.Bin, $j.Results)
    if ($TmaxSeconds -gt 0) { $sortArgs += @("--tmax", "$TmaxSeconds") }
    if ($DropFlagged) { $sortArgs += "--drop-flagged" }
    $t0 = Get-Date
    Add-Content $log "$(Get-Date -Format s)  START  $($j.Bin)"
    Write-Host "`n===== $($j.Bin) =====" -ForegroundColor Cyan
    & uv @sortArgs
    $code = $LASTEXITCODE
    $mins = [math]::Round(((Get-Date) - $t0).TotalMinutes, 1)
    $ok = ($code -eq 0) -and (Test-Path (Join-Path $j.Results "spike_times.npy"))
    if ($ok) { $status = "OK    " } else { $status = "FAILED"; $failed++ }
    Add-Content $log "$(Get-Date -Format s)  $status exit=$code  $mins min  $($j.Results)"
}

Add-Content $log "$(Get-Date -Format s)  ALL DONE, $failed failed"
Write-Host "`nAll done, $failed failed. Summary: $log"
if ($Shutdown) {
    Write-Host "Shutting down in 5 minutes. Cancel with: shutdown /a"
    shutdown /s /t 300 /c "sort_all.ps1 finished"
}
if ($Logout) {
    Write-Host "Signing out in 60 seconds. Press Ctrl+C to cancel."
    Start-Sleep -Seconds 60
    shutdown /l
}
exit $failed
