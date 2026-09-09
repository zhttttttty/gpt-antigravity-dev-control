[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$runtime = Join-Path $env:TEMP ("antigravity-protocol-test-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $runtime | Out-Null
$compiler = Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if (-not (Test-Path $compiler)) { $compiler = Join-Path $env:WINDIR "Microsoft.NET\Framework\v4.0.30319\csc.exe" }
$fakeAgy = Join-Path $runtime "fake-agy.exe"
& $compiler /nologo /target:exe ("/out:" + $fakeAgy) (Join-Path $PSScriptRoot "fixtures\fake_agy.cs")
if ($LASTEXITCODE -ne 0) { throw "Failed to compile fake agy" }

$launch = Join-Path $repo ".agents\skills\antigravity-delegate\scripts\launch_agents.ps1"
$collect = Join-Path $repo ".agents\skills\antigravity-delegate\scripts\collect_reports.ps1"

function Assert-True([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}

function Save-Config($Value, [string]$Path) {
    $Value | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $Path -Encoding UTF8
}

function Run-Pair([string]$Name, [string]$Mode) {
    $output = Join-Path $runtime $Name
    New-Item -ItemType Directory -Path $output | Out-Null
    $configPath = Join-Path $output "agents.json"
    Save-Config ([ordered]@{ tasks = @(
        [ordered]@{ name = "first"; worktree = $repo; mode = $Mode; prompt = "SLEEP:400 first"; max_retries = 0 },
        [ordered]@{ name = "second"; worktree = $repo; mode = $Mode; prompt = "SLEEP:400 second"; max_retries = 0 }
    ) }) $configPath
    & powershell -NoProfile -ExecutionPolicy Bypass -File $launch -ConfigPath $configPath -OutputDir $output -Executable $fakeAgy -MaxConcurrency 2 -MaxRetries 0 -DefaultTimeoutSeconds 60 | Out-Null
    Assert-True ($LASTEXITCODE -eq 0) "$Name launch failed"
    $sessions = (Get-Content (Join-Path $output "sessions.json") -Raw | ConvertFrom-Json).sessions
    $firstStart = [datetime]$sessions[0].attempts[0].started_utc
    $firstEnd = [datetime]$sessions[0].attempts[0].completed_utc
    $secondStart = [datetime]$sessions[1].attempts[0].started_utc
    $secondEnd = [datetime]$sessions[1].attempts[0].completed_utc
    return (($firstStart -lt $secondEnd) -and ($secondStart -lt $firstEnd))
}

$writerOverlap = Run-Pair "writers" "accept-edits"
$readerOverlap = Run-Pair "readers" "plan"
Assert-True (-not $writerOverlap) "Writers overlapped in the same worktree"
Assert-True $readerOverlap "Read-only agents did not run concurrently"

$largeOutput = Join-Path $runtime "large-output"
New-Item -ItemType Directory -Path $largeOutput | Out-Null
$largeConfig = Join-Path $largeOutput "agents.json"
Save-Config ([ordered]@{ tasks = @(
    [ordered]@{ name = "large"; worktree = $repo; mode = "plan"; prompt = "OUTPUT_BYTES:1000000"; max_retries = 0 }
) }) $largeConfig
& powershell -NoProfile -ExecutionPolicy Bypass -File $launch -ConfigPath $largeConfig -OutputDir $largeOutput -Executable $fakeAgy -MaxConcurrency 1 -MaxRetries 0 -DefaultTimeoutSeconds 60 | Out-Null
Assert-True ($LASTEXITCODE -eq 0) "Large stdout launch failed"
Assert-True ((Get-Item (Join-Path $largeOutput "large.md")).Length -ge 1000000) "Large stdout was truncated or blocked"

$dagOutput = Join-Path $runtime "dag-retry"
New-Item -ItemType Directory -Path $dagOutput | Out-Null
$marker = Join-Path $dagOutput "retry.marker"
$dagConfig = Join-Path $dagOutput "agents.json"
Save-Config ([ordered]@{ tasks = @(
    [ordered]@{ name = "full"; worktree = $repo; mode = "plan"; prompt = "SLEEP:150 full"; max_retries = 0 },
    [ordered]@{ name = "retry"; worktree = $repo; mode = "plan"; prompt = ("FAIL_ONCE:" + $marker + " retry") },
    [ordered]@{ name = "backend"; worktree = $repo; mode = "accept-edits"; prompt = "backend"; depends_on = @("full") }
) }) $dagConfig
& powershell -NoProfile -ExecutionPolicy Bypass -File $launch -ConfigPath $dagConfig -OutputDir $dagOutput -Executable $fakeAgy -MaxConcurrency 2 -MaxRetries 1 -DefaultTimeoutSeconds 60 | Out-Null
Assert-True ($LASTEXITCODE -eq 0) "DAG/retry launch failed"
$dagRegistry = Get-Content (Join-Path $dagOutput "sessions.json") -Raw | ConvertFrom-Json
$retry = @($dagRegistry.sessions | Where-Object { $_.name -eq "retry" })[0]
$backend = @($dagRegistry.sessions | Where-Object { $_.name -eq "backend" })[0]
Assert-True ($dagRegistry.effective_max_concurrency -eq 1) "Failure did not reduce concurrency"
Assert-True ($retry.attempts.Count -eq 2) "Failed task was not retried exactly once"
Assert-True ($backend.planned_wave -eq 2) "Dependency wave was not calculated"
& powershell -NoProfile -ExecutionPolicy Bypass -File $collect -OutputDir $dagOutput | Out-Null
Assert-True ($LASTEXITCODE -eq 0) "Report collection failed"
Assert-True (Test-Path (Join-Path $dagOutput "summary.json")) "summary.json missing"
Assert-True (Test-Path (Join-Path $dagOutput "handoff.md")) "handoff.md missing"

$cycleOutput = Join-Path $runtime "cycle"
New-Item -ItemType Directory -Path $cycleOutput | Out-Null
$cycleConfig = Join-Path $cycleOutput "agents.json"
Save-Config ([ordered]@{ tasks = @(
    [ordered]@{ name = "a"; worktree = $repo; mode = "plan"; prompt = "a"; depends_on = @("b") },
    [ordered]@{ name = "b"; worktree = $repo; mode = "plan"; prompt = "b"; depends_on = @("a") }
) }) $cycleConfig
$savedPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& powershell -NoProfile -ExecutionPolicy Bypass -File $launch -ConfigPath $cycleConfig -OutputDir $cycleOutput -Executable $fakeAgy -DryRun 2>&1 | Out-Null
$cycleExit = $LASTEXITCODE
$ErrorActionPreference = $savedPreference
Assert-True ($cycleExit -eq 2) "Dependency cycle was not rejected with exit 2"

$lockOutput = Join-Path $runtime "lock"
New-Item -ItemType Directory -Path $lockOutput | Out-Null
$lockConfig = Join-Path $lockOutput "agents.json"
$lockPath = Join-Path $lockOutput "controller.lock"
Save-Config ([ordered]@{ tasks = @(
    [ordered]@{ name = "locked"; worktree = $repo; mode = "plan"; prompt = "locked"; max_retries = 0 }
) }) $lockConfig
$heldLock = [IO.File]::Open($lockPath, [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
try {
    $savedPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & powershell -NoProfile -ExecutionPolicy Bypass -File $launch -ConfigPath $lockConfig -OutputDir $lockOutput -Executable $fakeAgy -LockPath $lockPath -MaxRetries 0 2>&1 | Out-Null
    $lockExit = $LASTEXITCODE
    $ErrorActionPreference = $savedPreference
} finally {
    $heldLock.Dispose()
}
Assert-True ($lockExit -eq 2) "Concurrent launcher lock was not enforced"

Write-Output "Multi-agent protocol tests passed"
