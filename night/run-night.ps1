$repo    = "D:\cognitive-os\polymath-os-android"
$pidsDir = "D:\cognitive-os\night\pids"
$log     = "D:\cognitive-os\night\logs\$(Get-Date -Format yyyyMMdd-HHmm).log"
$lock    = "D:\cognitive-os\night\night.lock"
$night   = "D:\cognitive-os\night"

New-Item -ItemType Directory -Force -Path "$night\logs" | Out-Null
New-Item -ItemType Directory -Force -Path $pidsDir | Out-Null

# Lock guard: skip if another invocation is <55 min old
if (Test-Path $lock) {
    $age = (Get-Date) - (Get-Item $lock).LastWriteTime
    if ($age.TotalMinutes -lt 55) {
        "locked, skip" | Out-File $log
        exit
    }
}
New-Item -Force $lock | Out-Null

try {
    Set-Location $repo
    git fetch origin 2>&1 | Out-Null
    git pull --ff-only origin feat/ui-revamp-v4 2>&1 | Out-Null

    if (Test-Path "specs\tasks\NIGHT-DONE.flag") {
        "queue done - nothing to do" | Out-File $log
        exit
    }

    # Run the agent: headless, non-interactive
    # --settings: night profile (tool diet + no web/plan-mode)
    # Verify flag: confirmed as --settings <file> via claude --help (2026-07-19)
    $contract = Get-Content "$night\night-contract.md" -Raw
    claude -p $contract `
        --settings "$night\settings.night.json" `
        --max-turns 70 2>&1 | Tee-Object $log

} finally {
    # PID-file teardown: kill ONLY what we started, by recorded PID
    $pidFiles = Get-ChildItem -Path $pidsDir -Filter "*.pid" -ErrorAction SilentlyContinue
    foreach ($pidFile in $pidFiles) {
        $proc = [int](Get-Content $pidFile.FullName -ErrorAction SilentlyContinue)
        if ($proc -gt 0) {
            try {
                $p = Get-Process -Id $proc -ErrorAction SilentlyContinue
                if ($p) {
                    Stop-Process -Id $proc -Force -ErrorAction SilentlyContinue
                    "Stopped PID $proc ($($pidFile.BaseName))" | Out-File $log -Append
                }
            } catch {
                "WARN: could not stop PID $proc - note in morning report" | Out-File $log -Append
            }
            Remove-Item $pidFile.FullName -ErrorAction SilentlyContinue
        }
    }
    # cog-mongo: leave running (never stopped by night shift)
    $remaining = Get-ChildItem -Path $pidsDir -ErrorAction SilentlyContinue
    if ($remaining) {
        "WARN: pids\ not empty after teardown: $($remaining.Name -join ', ')" | Out-File $log -Append
    }
    Remove-Item $lock -ErrorAction SilentlyContinue
}
