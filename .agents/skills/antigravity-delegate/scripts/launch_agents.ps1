[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ConfigPath,
    [Parameter(Mandatory = $true)][string]$OutputDir,
    [string]$Executable = "agy",
    [string]$CapabilitiesPath = "",
    [ValidateRange(1,2)][int]$MaxConcurrency = 2,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Resolve-Native([string]$Name) {
    $command = Get-Command $Name -ErrorAction Stop
    $path = if ($command.Source) { $command.Source } else { $command.Path }
    if (-not $path) { throw "Unable to resolve executable: $Name" }
    if ([IO.Path]::GetExtension($path).ToLowerInvariant() -in @(".cmd", ".bat")) { throw "Native executable required: $path" }
    return [IO.Path]::GetFullPath($path)
}

function Save-Json($Value, [string]$Path) {
    $Value | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $Path -Encoding UTF8
}

function Quote-Windows([string]$Value) {
    if ($Value -notmatch '[\s"]') { return $Value }
    return '"' + ($Value -replace '(\\*)"', '$1$1\"' -replace '(\\+)$', '$1$1') + '"'
}

try {
    $exePath = Resolve-Native $Executable
    $out = [IO.Path]::GetFullPath($OutputDir)
    New-Item -ItemType Directory -Force -Path $out | Out-Null
    $config = Get-Content -LiteralPath ([IO.Path]::GetFullPath($ConfigPath)) -Raw | ConvertFrom-Json
    $items = @($config.tasks)
    if (-not $items.Count) { throw "Config must contain a non-empty tasks array" }
    if (-not $CapabilitiesPath) {
        $probeDir = Join-Path $out "probe"
        $probeScript = Join-Path $PSScriptRoot "probe_agy.ps1"
        & $probeScript -Executable $exePath -OutputDir $probeDir | Out-Null
        $CapabilitiesPath = Join-Path $probeDir "capabilities.json"
    }
    $cap = Get-Content -LiteralPath ([IO.Path]::GetFullPath($CapabilitiesPath)) -Raw | ConvertFrom-Json
    $runId = [guid]::NewGuid().ToString()
    $registryPath = Join-Path $out "sessions.json"
    $registry = [ordered]@{ run_id = $runId; executable = $exePath; max_concurrency = $MaxConcurrency; capabilities_file = [IO.Path]::GetFullPath($CapabilitiesPath); sessions = @() }
    foreach ($item in $items) {
        $name = [string]$item.name
        if (-not $name -or $name -notmatch '^[A-Za-z0-9._-]+$') { throw "Task names must be stable ASCII slugs: $name" }
        $mode = if ($item.mode) { [string]$item.mode } else { "accept-edits" }
        if ($mode -notin @("accept-edits", "plan")) { throw "Unsupported controller launch mode: $mode" }
        if ($mode -eq "plan" -and (-not (@($cap.capabilities.mode_values) -contains "plan"))) { throw "agy does not advertise plan mode" }
        if ($mode -eq "accept-edits" -and (@($cap.capabilities.mode_values).Count -gt 0) -and (-not (@($cap.capabilities.mode_values) -contains "accept-edits"))) { throw "agy does not advertise accept-edits mode" }
        $worktree = [IO.Path]::GetFullPath([string]$item.worktree)
        $prompt = [string]$item.prompt
        if ($mode -eq "plan") { $prompt = "READ-ONLY REVIEW. Do not create, edit, delete, commit, merge, or push files." + [Environment]::NewLine + $prompt }
        $report = Join-Path $out ($name + ".md")
        $log = Join-Path $out ($name + ".execution.log")
        $err = Join-Path $out ($name + ".stderr.log")
        $argv = [System.Collections.Generic.List[string]]::new()
        $argv.Add("--add-dir"); $argv.Add($worktree); $argv.Add("--mode"); $argv.Add($mode); $argv.Add("--output-format"); $argv.Add("text"); $argv.Add("--print-timeout"); $argv.Add("20m"); $argv.Add("--print=" + $prompt); $argv.Add("--log-file"); $argv.Add($log)
        if ($item.effort) { $argv.Add("--effort"); $argv.Add([string]$item.effort) }
        if ($item.model) { $argv.Add("--model"); $argv.Add([string]$item.model) }
        if ([bool]$item.auto_approve) {
            if (-not [bool]$cap.capabilities.permission_bypass) { throw "auto_approve requested but --dangerously-skip-permissions is unavailable" }
            $argv.Add("--dangerously-skip-permissions")
        }
        $record = [ordered]@{ name = $name; session_id = $null; status = "queued"; attempt = if ($item.attempt) { [int]$item.attempt } else { 1 }; report = $report; execution_log = $log; error_log = $err; argv = @($argv) }
        if ($DryRun) { $record.status = "dry-run"; $registry.sessions += [pscustomobject]$record; continue }
        $registry.sessions += [pscustomobject]$record
    }
    Save-Json $registry $registryPath
    if ($DryRun) { Write-Output (($registry | ConvertTo-Json -Depth 20)); exit 0 }
    $running = @{}
    $queue = [System.Collections.Queue]::new()
    foreach ($item in $items) { $queue.Enqueue($item) }
    while ($queue.Count -gt 0 -or $running.Count -gt 0) {
        while ($queue.Count -gt 0 -and $running.Count -lt $MaxConcurrency) {
            $item = $queue.Dequeue(); $record = @($registry.sessions | Where-Object { $_.name -eq $item.name })[0]
            $mode = if ($item.mode) { [string]$item.mode } else { "accept-edits" }; $prompt = [string]$item.prompt
            if ($mode -eq "plan") { $prompt = "READ-ONLY REVIEW. Do not create, edit, delete, commit, merge, or push files." + [Environment]::NewLine + $prompt }
            $argsList = [System.Collections.Generic.List[string]]::new(); $argsList.Add("--add-dir"); $argsList.Add([IO.Path]::GetFullPath([string]$item.worktree)); $argsList.Add("--mode"); $argsList.Add($mode); $argsList.Add("--output-format"); $argsList.Add("text"); $argsList.Add("--print-timeout"); $argsList.Add("20m"); $argsList.Add("--print=" + $prompt); $argsList.Add("--log-file"); $argsList.Add($record.execution_log)
            if ($item.effort) { $argsList.Add("--effort"); $argsList.Add([string]$item.effort) }; if ($item.model) { $argsList.Add("--model"); $argsList.Add([string]$item.model) }; if ([bool]$item.auto_approve) { $argsList.Add("--dangerously-skip-permissions") }
            $psi = [Diagnostics.ProcessStartInfo]::new(); $psi.FileName = $exePath; $psi.UseShellExecute = $false; $psi.RedirectStandardOutput = $true; $psi.RedirectStandardError = $true; $psi.CreateNoWindow = $true
            foreach ($arg in $argsList) { try { $psi.ArgumentList.Add($arg) } catch { $psi.Arguments += (Quote-Windows $arg) + " " } }
            $psi.WorkingDirectory = [IO.Path]::GetFullPath([string]$item.worktree)
            $process = [Diagnostics.Process]::new(); $process.StartInfo = $psi
            if (-not $process.Start()) { throw "Failed to start $($item.name)" }
            $record.session_id = [string]$process.Id; $record.status = "running"; $running[$process.Id] = [pscustomobject]@{ process = $process; record = $record; item = $item }
            Save-Json $registry $registryPath
        }
        foreach ($key in @($running.Keys)) {
            $job = $running[$key]; if (-not $job.process.HasExited) { continue }
            $stdout = $job.process.StandardOutput.ReadToEnd(); $stderr = $job.process.StandardError.ReadToEnd(); Set-Content -LiteralPath $job.record.report -Value $stdout -Encoding UTF8; Set-Content -LiteralPath $job.record.error_log -Value $stderr -Encoding UTF8
            $job.record.status = if ($job.process.ExitCode -eq 0) { "completed" } else { "failed" }; $job.record.exit_code = $job.process.ExitCode; $running.Remove($key); Save-Json $registry $registryPath
        }
        Start-Sleep -Milliseconds 250
    }
    Write-Output (($registry | ConvertTo-Json -Depth 20)); exit 0
} catch { Write-Error (([ordered]@{ error = $_.Exception.Message } | ConvertTo-Json -Compress)); exit 2 }
