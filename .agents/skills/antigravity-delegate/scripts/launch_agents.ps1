[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ConfigPath,
    [Parameter(Mandatory = $true)][string]$OutputDir,
    [string]$Executable = "agy",
    [string]$CapabilitiesPath = "",
    [ValidateRange(1,4)][int]$MaxConcurrency = 2,
    [switch]$AllowHighWriteConcurrency,
    [ValidateRange(0,1)][int]$MaxRetries = 1,
    [ValidateRange(30,86400)][int]$DefaultTimeoutSeconds = 1260,
    [string]$LockPath = "",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$lockStream = $null
$resultJson = $null
$failureJson = $null
$exitCode = 0

function Resolve-Native([string]$Name) {
    $command = Get-Command $Name -ErrorAction Stop
    $path = if ($command.Source) { $command.Source } else { $command.Path }
    if (-not $path) { throw "Unable to resolve executable: $Name" }
    if ([IO.Path]::GetExtension($path).ToLowerInvariant() -in @(".cmd", ".bat")) {
        throw "Native executable required: $path"
    }
    return [IO.Path]::GetFullPath($path)
}

function Save-Json($Value, [string]$Path) {
    $temporary = $Path + ".tmp"
    $Value | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $temporary -Encoding UTF8
    Move-Item -LiteralPath $temporary -Destination $Path -Force
}

function Quote-Windows([string]$Value) {
    if ($Value -notmatch '[\s"]') { return $Value }
    return '"' + ($Value -replace '(\\*)"', '$1$1\"' -replace '(\\+)$', '$1$1') + '"'
}

function Get-TextSha256([string]$Value) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [Text.Encoding]::UTF8.GetBytes($Value)
        return ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace("-", "").ToLowerInvariant()
    } finally {
        $sha.Dispose()
    }
}

function Test-SamePath([string]$Left, [string]$Right) {
    return [string]::Equals(
        [IO.Path]::GetFullPath($Left).TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar),
        [IO.Path]::GetFullPath($Right).TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar),
        [StringComparison]::OrdinalIgnoreCase
    )
}

try {
    $exePath = Resolve-Native $Executable
    $out = [IO.Path]::GetFullPath($OutputDir)
    New-Item -ItemType Directory -Force -Path $out | Out-Null

    if (-not $CapabilitiesPath) {
        $probeDir = Join-Path $out "probe"
        $probeScript = Join-Path $PSScriptRoot "probe_agy.ps1"
        & $probeScript -Executable $exePath -OutputDir $probeDir | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "agy capability probe failed; inspect $probeDir" }
        $CapabilitiesPath = Join-Path $probeDir "capabilities.json"
    }
    $capabilityFile = [IO.Path]::GetFullPath($CapabilitiesPath)
    $cap = Get-Content -LiteralPath $capabilityFile -Raw | ConvertFrom-Json
    if (-not [bool]$cap.available) { throw "agy capability record reports unavailable" }

    $config = Get-Content -LiteralPath ([IO.Path]::GetFullPath($ConfigPath)) -Raw | ConvertFrom-Json
    $items = @($config.tasks)
    if (-not $items.Count) { throw "Config must contain a non-empty tasks array" }

    $runId = [guid]::NewGuid().ToString()
    $registryPath = Join-Path $out "sessions.json"
    $registry = [ordered]@{
        run_id = $runId
        status = "preparing"
        executable = $exePath
        requested_max_concurrency = $MaxConcurrency
        target_max_concurrency = $MaxConcurrency
        effective_max_concurrency = [Math]::Min($MaxConcurrency, 2)
        concurrency_policy = "standard"
        writer_concurrency_capped = $false
        ramp_up_pending = ($MaxConcurrency -gt 2)
        ramp_up_completed = $false
        ramp_up_aborted = $false
        downgraded_to_serial = $false
        max_retries = $MaxRetries
        capabilities_file = $capabilityFile
        lock_file = $null
        started_utc = [DateTime]::UtcNow.ToString("o")
        completed_utc = $null
        sessions = @()
    }
    $itemByName = @{}
    $sessionByName = @{}
    $taskOrder = 0

    foreach ($item in $items) {
        $name = [string]$item.name
        if (-not $name -or $name -notmatch '^[A-Za-z0-9._-]+$') {
            throw "Task names must be stable ASCII slugs: $name"
        }
        if ($itemByName.ContainsKey($name)) { throw "Duplicate task name: $name" }
        $mode = if ($item.mode) { [string]$item.mode } else { "accept-edits" }
        if ($mode -notin @("accept-edits", "plan")) { throw "Unsupported agy mode for ${name}: $mode" }
        if (-not (@($cap.capabilities.mode_values) -contains $mode)) {
            throw "agy does not advertise mode $mode for $name"
        }
        if ([bool]$item.auto_approve -and -not [bool]$cap.capabilities.permission_bypass) {
            throw "auto_approve requested for $name but permission bypass is unavailable"
        }
        $worktree = [IO.Path]::GetFullPath([string]$item.worktree)
        if (-not (Test-Path -LiteralPath $worktree -PathType Container)) {
            throw "Worktree does not exist for ${name}: $worktree"
        }
        $gitRoot = (& git -C $worktree rev-parse --show-toplevel 2>$null | Out-String).Trim()
        if ($LASTEXITCODE -ne 0 -or -not $gitRoot) { throw "Task worktree is not a Git worktree: $worktree" }
        $dependencies = @($item.depends_on | ForEach-Object { [string]$_ } | Where-Object { $_ })
        $initialAttempt = if ($item.attempt) { [int]$item.attempt } else { 1 }
        $taskRetries = if ($null -ne $item.max_retries) { [Math]::Min([int]$item.max_retries, $MaxRetries) } else { $MaxRetries }
        $timeoutSeconds = if ($item.timeout_seconds) { [int]$item.timeout_seconds } else { $DefaultTimeoutSeconds }
        if ($timeoutSeconds -lt 30 -or $timeoutSeconds -gt 86400) { throw "timeout_seconds for $name must be 30..86400" }
        $prompt = [string]$item.prompt
        if (-not $prompt.Trim()) { throw "Task prompt is empty: $name" }
        $promptHash = Get-TextSha256 $prompt
        $previewMinutes = [Math]::Max(1, [Math]::Ceiling($timeoutSeconds / 60.0))
        $argvPreview = @("--add-dir", [IO.Path]::GetFullPath($gitRoot), "--mode", $mode, "--output-format", "text", "--print-timeout", (([int]$previewMinutes).ToString() + "m"), "--print=<prompt sha256:$promptHash>", "--log-file=<attempt-specific>")
        if ($item.effort) { $argvPreview += @("--effort", [string]$item.effort) }
        if ($item.model) { $argvPreview += @("--model", [string]$item.model) }
        if ([bool]$item.auto_approve) { $argvPreview += "--dangerously-skip-permissions" }
        $record = [pscustomobject][ordered]@{
            name = $name
            order = $taskOrder
            mode = $mode
            writes = ($mode -ne "plan")
            worktree = [IO.Path]::GetFullPath($gitRoot)
            depends_on = $dependencies
            planned_wave = 0
            status = "queued"
            attempt = $initialAttempt
            max_attempts = $initialAttempt + $taskRetries
            timeout_seconds = $timeoutSeconds
            session_id = $null
            report = Join-Path $out ($name + ".md")
            execution_log = $null
            error_log = $null
            exit_code = $null
            failure_reason = $null
            prompt_sha256 = $promptHash
            argv_preview = $argvPreview
            started_utc = $null
            completed_utc = $null
            attempts = @()
        }
        $itemByName[$name] = $item
        $sessionByName[$name] = $record
        $registry.sessions += $record
        $taskOrder++
    }

    foreach ($record in @($registry.sessions)) {
        foreach ($dependency in @($record.depends_on)) {
            if (-not $sessionByName.ContainsKey($dependency)) { throw "Unknown dependency for $($record.name): $dependency" }
            if ($dependency -eq $record.name) { throw "Task cannot depend on itself: $dependency" }
        }
    }

    $targetConcurrency = [Math]::Min($MaxConcurrency, @($registry.sessions).Count)
    $hasWriters = (@($registry.sessions | Where-Object { $_.writes })).Count -gt 0
    if ($hasWriters -and $targetConcurrency -gt 2 -and -not $AllowHighWriteConcurrency) {
        $targetConcurrency = 2
        $registry.writer_concurrency_capped = $true
        $registry.concurrency_policy = "writer-safe-cap"
    } elseif ($targetConcurrency -gt 2 -and $hasWriters) {
        $registry.concurrency_policy = "explicit-high-write"
    } elseif ($targetConcurrency -gt 2) {
        $registry.concurrency_policy = "read-only-ramp"
    }
    $registry.target_max_concurrency = $targetConcurrency
    $registry.effective_max_concurrency = [Math]::Min($targetConcurrency, 2)
    $registry.ramp_up_pending = ($targetConcurrency -gt 2)

    $remaining = @{}
    foreach ($record in @($registry.sessions)) { $remaining[$record.name] = $record }
    while ($remaining.Count -gt 0) {
        $progress = $false
        foreach ($name in @($remaining.Keys)) {
            $record = $remaining[$name]
            $ready = $true
            $wave = 1
            foreach ($dependency in @($record.depends_on)) {
                if ($remaining.ContainsKey($dependency)) { $ready = $false; break }
                $wave = [Math]::Max($wave, [int]$sessionByName[$dependency].planned_wave + 1)
            }
            if ($ready) {
                $record.planned_wave = $wave
                $remaining.Remove($name)
                $progress = $true
            }
        }
        if (-not $progress) { throw "Dependency cycle detected in agent task graph" }
    }

    if ($DryRun) {
        foreach ($record in @($registry.sessions)) { $record.status = "dry-run" }
        $registry.status = "dry-run"
        $registry.completed_utc = [DateTime]::UtcNow.ToString("o")
        Save-Json $registry $registryPath
        $resultJson = $registry | ConvertTo-Json -Depth 30
    } else {
        if (-not $LockPath) {
            $lockRoot = if ($env:LOCALAPPDATA) { Join-Path $env:LOCALAPPDATA "agy" } else { Split-Path $out -Parent }
            New-Item -ItemType Directory -Force -Path $lockRoot | Out-Null
            $LockPath = Join-Path $lockRoot "codex-antigravity-delegate.lock"
        }
        $resolvedLock = [IO.Path]::GetFullPath($LockPath)
        try {
            $lockStream = [IO.File]::Open($resolvedLock, [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
        } catch {
            throw "Another Antigravity delegation controller is active; lock unavailable: $resolvedLock"
        }
        $lockBytes = [Text.Encoding]::UTF8.GetBytes(("pid={0};run_id={1};started_utc={2}" -f $PID, $runId, $registry.started_utc))
        $lockStream.SetLength(0)
        $lockStream.Write($lockBytes, 0, $lockBytes.Length)
        $lockStream.Flush()
        $registry.lock_file = $resolvedLock
        $registry.status = "running"
        Save-Json $registry $registryPath

        $running = @{}
        while ((@($registry.sessions | Where-Object { $_.status -in @("queued", "running") })).Count -gt 0) {
            foreach ($record in @($registry.sessions | Where-Object { $_.status -eq "queued" })) {
                $dependencyFailure = @($record.depends_on | Where-Object { $sessionByName[$_].status -in @("failed", "blocked") })
                if ($dependencyFailure.Count -gt 0) {
                    $record.status = "blocked"
                    $record.failure_reason = "dependency_failed: " + ($dependencyFailure -join ",")
                    $record.completed_utc = [DateTime]::UtcNow.ToString("o")
                }
            }

            $startedOne = $true
            while ($running.Count -lt [int]$registry.effective_max_concurrency -and $startedOne) {
                $startedOne = $false
                foreach ($record in @($registry.sessions | Where-Object { $_.status -eq "queued" } | Sort-Object planned_wave, order)) {
                    $dependenciesReady = (@($record.depends_on | Where-Object { $sessionByName[$_].status -ne "completed" })).Count -eq 0
                    if (-not $dependenciesReady) { continue }
                    $resourceAvailable = $true
                    foreach ($job in @($running.Values)) {
                        if ((Test-SamePath $record.worktree $job.record.worktree) -and ($record.writes -or $job.record.writes)) {
                            $resourceAvailable = $false
                            break
                        }
                    }
                    if (-not $resourceAvailable) { continue }

                    $item = $itemByName[$record.name]
                    $prompt = [string]$item.prompt
                    if ($record.mode -eq "plan") {
                        $prompt = "READ-ONLY REVIEW. Do not create, edit, delete, commit, merge, or push files." + [Environment]::NewLine + $prompt
                    }
                    if (@($record.depends_on).Count -gt 0) {
                        $hints = @($record.depends_on | ForEach-Object { $_ + "=" + $sessionByName[$_].report })
                        $prompt += [Environment]::NewLine + "Read these completed dependency reports before starting: " + ($hints -join "; ")
                    }
                    $attemptPrefix = $record.name + ".attempt-" + $record.attempt
                    $attemptReport = Join-Path $out ($attemptPrefix + ".md")
                    $attemptLog = Join-Path $out ($attemptPrefix + ".execution.log")
                    $attemptError = Join-Path $out ($attemptPrefix + ".stderr.log")
                    $minutes = [Math]::Max(1, [Math]::Ceiling($record.timeout_seconds / 60.0))
                    $argsList = [System.Collections.Generic.List[string]]::new()
                    $argsList.Add("--add-dir"); $argsList.Add($record.worktree)
                    $argsList.Add("--mode"); $argsList.Add($record.mode)
                    $argsList.Add("--output-format"); $argsList.Add("text")
                    $argsList.Add("--print-timeout"); $argsList.Add(([int]$minutes).ToString() + "m")
                    $argsList.Add("--print=" + $prompt)
                    $argsList.Add("--log-file"); $argsList.Add($attemptLog)
                    if ($item.effort) { $argsList.Add("--effort"); $argsList.Add([string]$item.effort) }
                    if ($item.model) { $argsList.Add("--model"); $argsList.Add([string]$item.model) }
                    if ([bool]$item.auto_approve) { $argsList.Add("--dangerously-skip-permissions") }

                    $psi = [Diagnostics.ProcessStartInfo]::new()
                    $psi.FileName = $exePath
                    $psi.UseShellExecute = $false
                    $psi.RedirectStandardOutput = $true
                    $psi.RedirectStandardError = $true
                    $psi.CreateNoWindow = $true
                    $psi.WorkingDirectory = $record.worktree
                    foreach ($arg in $argsList) {
                        try { $psi.ArgumentList.Add($arg) } catch { $psi.Arguments += (Quote-Windows $arg) + " " }
                    }
                    $process = [Diagnostics.Process]::new()
                    $process.StartInfo = $psi
                    if (-not $process.Start()) { throw "Failed to start $($record.name)" }
                    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
                    $stderrTask = $process.StandardError.ReadToEndAsync()
                    $startedUtc = [DateTime]::UtcNow
                    $record.session_id = [string]$process.Id
                    $record.status = "running"
                    $record.started_utc = $startedUtc.ToString("o")
                    $record.execution_log = $attemptLog
                    $record.error_log = $attemptError
                    $record.exit_code = $null
                    $record.failure_reason = $null
                    $running[$process.Id] = [pscustomobject]@{
                        process = $process
                        stdout_task = $stdoutTask
                        stderr_task = $stderrTask
                        record = $record
                        report = $attemptReport
                        error_log = $attemptError
                        started_utc = $startedUtc
                    }
                    $startedOne = $true
                    Save-Json $registry $registryPath
                    break
                }
            }

            foreach ($key in @($running.Keys)) {
                $job = $running[$key]
                $timedOut = (([DateTime]::UtcNow - $job.started_utc).TotalSeconds -gt $job.record.timeout_seconds)
                if (-not $job.process.HasExited -and -not $timedOut) { continue }
                if ($timedOut -and -not $job.process.HasExited) {
                    try { $job.process.Kill($true) } catch { try { $job.process.Kill() } catch {} }
                }
                $job.process.WaitForExit()
                $stdout = $job.stdout_task.GetAwaiter().GetResult()
                $stderr = $job.stderr_task.GetAwaiter().GetResult()
                Set-Content -LiteralPath $job.report -Value $stdout -Encoding UTF8
                Set-Content -LiteralPath $job.record.report -Value $stdout -Encoding UTF8
                Set-Content -LiteralPath $job.error_log -Value $stderr -Encoding UTF8
                $attemptStatus = if ($timedOut) { "timed_out" } elseif ($job.process.ExitCode -eq 0) { "completed" } else { "failed" }
                $attemptRecord = [pscustomobject][ordered]@{
                    attempt = $job.record.attempt
                    session_id = [string]$job.process.Id
                    status = $attemptStatus
                    exit_code = if ($timedOut) { $null } else { $job.process.ExitCode }
                    report = $job.report
                    execution_log = $job.record.execution_log
                    error_log = $job.error_log
                    started_utc = $job.record.started_utc
                    completed_utc = [DateTime]::UtcNow.ToString("o")
                }
                $job.record.attempts += $attemptRecord
                $job.record.completed_utc = $attemptRecord.completed_utc
                if ($attemptStatus -eq "completed") {
                    $job.record.status = "completed"
                    $job.record.exit_code = $job.process.ExitCode
                    if ($registry.ramp_up_pending -and -not $registry.downgraded_to_serial) {
                        $registry.effective_max_concurrency = $registry.target_max_concurrency
                        $registry.ramp_up_pending = $false
                        $registry.ramp_up_completed = $true
                    }
                } elseif ($job.record.attempt -lt $job.record.max_attempts) {
                    $job.record.status = "queued"
                    $job.record.failure_reason = $attemptStatus
                    $job.record.attempt = [int]$job.record.attempt + 1
                    $job.record.session_id = $null
                    $registry.effective_max_concurrency = 1
                    $registry.downgraded_to_serial = $true
                    $registry.ramp_up_pending = $false
                    $registry.ramp_up_aborted = $true
                } else {
                    $job.record.status = "failed"
                    $job.record.exit_code = if ($timedOut) { $null } else { $job.process.ExitCode }
                    $job.record.failure_reason = $attemptStatus
                }
                $running.Remove($key)
                $job.process.Dispose()
                Save-Json $registry $registryPath
            }

            if ($running.Count -eq 0 -and (@($registry.sessions | Where-Object { $_.status -eq "queued" })).Count -gt 0) {
                $startable = @($registry.sessions | Where-Object {
                    $_.status -eq "queued" -and (@($_.depends_on | Where-Object { $sessionByName[$_].status -ne "completed" })).Count -eq 0
                })
                if ($startable.Count -eq 0) {
                    foreach ($record in @($registry.sessions | Where-Object { $_.status -eq "queued" })) {
                        $record.status = "blocked"
                        $record.failure_reason = "dependencies_not_completed"
                        $record.completed_utc = [DateTime]::UtcNow.ToString("o")
                    }
                }
            }
            Start-Sleep -Milliseconds 250
        }

        $failedCount = @($registry.sessions | Where-Object { $_.status -in @("failed", "blocked") }).Count
        $registry.status = if ($failedCount -gt 0) { "failed" } else { "completed" }
        $registry.completed_utc = [DateTime]::UtcNow.ToString("o")
        Save-Json $registry $registryPath
        $resultJson = $registry | ConvertTo-Json -Depth 30
        if ($failedCount -gt 0) { $exitCode = 2 }
    }
} catch {
    $failureJson = [ordered]@{ error = $_.Exception.Message } | ConvertTo-Json -Compress
    $exitCode = 2
} finally {
    if ($lockStream) { $lockStream.Dispose() }
}

if ($failureJson) { [Console]::Error.WriteLine($failureJson) } else { Write-Output $resultJson }
exit $exitCode
