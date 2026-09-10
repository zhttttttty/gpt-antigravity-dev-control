[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$OutputDir,
    [ValidateRange(0,20000)][int]$PreviewChars = 2000,
    [string]$OutputFile = ""
)

$ErrorActionPreference = "Stop"

function Save-Text([string]$Value, [string]$Path) {
    $temporary = $Path + ".tmp"
    Set-Content -LiteralPath $temporary -Value $Value -Encoding UTF8
    Move-Item -LiteralPath $temporary -Destination $Path -Force
}

try {
    $out = [IO.Path]::GetFullPath($OutputDir)
    $registryPath = Join-Path $out "sessions.json"
    $registry = Get-Content -LiteralPath $registryPath -Raw | ConvertFrom-Json
    $reports = @()
    $completed = 0
    $failed = 0
    $blocked = 0
    $missing = 0

    foreach ($session in @($registry.sessions)) {
        $exists = Test-Path -LiteralPath $session.report -PathType Leaf
        $preview = ""
        $hash = $null
        if ($exists) {
            $text = Get-Content -LiteralPath $session.report -Raw
            if ($PreviewChars -gt 0) { $preview = $text.Substring(0, [Math]::Min($PreviewChars, $text.Length)) }
            $hash = (Get-FileHash -LiteralPath $session.report -Algorithm SHA256).Hash.ToLowerInvariant()
        }
        if ($session.status -eq "completed" -and $exists) { $completed++ }
        if ($session.status -eq "completed" -and -not $exists) { $missing++ }
        if ($session.status -eq "failed") { $failed++ }
        if ($session.status -eq "blocked") { $blocked++ }
        $reports += [ordered]@{
            name = $session.name
            mode = $session.mode
            status = $session.status
            planned_wave = $session.planned_wave
            depends_on = @($session.depends_on)
            worktree = $session.worktree
            attempt = $session.attempt
            attempts = @($session.attempts)
            report = $session.report
            report_exists = $exists
            report_sha256 = $hash
            preview = $preview
            exit_code = $session.exit_code
            failure_reason = $session.failure_reason
            execution_log = $session.execution_log
            error_log = $session.error_log
        }
    }

    $duplicateGroups = @()
    foreach ($group in @($reports | Where-Object { $_.report_sha256 } | Group-Object report_sha256 | Where-Object { $_.Count -gt 1 })) {
        $duplicateGroups += [ordered]@{ report_sha256 = $group.Name; agents = @($group.Group | ForEach-Object { $_.name }) }
    }
    $total = @($registry.sessions).Count
    $summaryStatus = if (($failed + $blocked + $missing) -gt 0) {
        "FAILED"
    } elseif ($completed -eq $total) {
        "COMPLETE"
    } else {
        "INCOMPLETE"
    }
    $handoffPath = Join-Path $out "handoff.md"
    $summary = [ordered]@{
        run_id = $registry.run_id
        status = $summaryStatus
        requested_max_concurrency = $registry.requested_max_concurrency
        target_max_concurrency = $registry.target_max_concurrency
        effective_max_concurrency = $registry.effective_max_concurrency
        concurrency_policy = $registry.concurrency_policy
        writer_concurrency_capped = $registry.writer_concurrency_capped
        ramp_up_completed = $registry.ramp_up_completed
        ramp_up_aborted = $registry.ramp_up_aborted
        downgraded_to_serial = $registry.downgraded_to_serial
        total = $total
        completed = $completed
        failed = $failed
        blocked = $blocked
        missing_reports = $missing
        duplicate_report_groups = $duplicateGroups
        handoff = $handoffPath
        reports = $reports
        generated_utc = [DateTime]::UtcNow.ToString("o")
    }
    if (-not $OutputFile) { $OutputFile = Join-Path $out "summary.json" }
    $outputPath = [IO.Path]::GetFullPath($OutputFile)
    Save-Text ($summary | ConvertTo-Json -Depth 30) $outputPath

    $lines = [Collections.Generic.List[string]]::new()
    $lines.Add("# Antigravity delegation handoff")
    $lines.Add("")
    $lines.Add("Run: " + $registry.run_id)
    $lines.Add("Status: " + $summaryStatus)
    $lines.Add("Concurrency: requested " + $registry.requested_max_concurrency + ", target " + $registry.target_max_concurrency + ", effective " + $registry.effective_max_concurrency + ", policy " + $registry.concurrency_policy)
    $lines.Add("")
    $lines.Add("## Agent results")
    $lines.Add("")
    foreach ($report in $reports) {
        $dependencyText = if (@($report.depends_on).Count) { @($report.depends_on) -join ", " } else { "none" }
        $lines.Add("- " + $report.name + ": " + $report.status + "; wave " + $report.planned_wave + "; dependencies " + $dependencyText + "; report " + $report.report)
    }
    $lines.Add("")
    $lines.Add("## Codex verification")
    $lines.Add("")
    $lines.Add("Verify P0/P1 evidence, paths and line numbers; run repository tests; check each worktree; merge duplicate findings; classify conclusions as CONFIRMED, CONDITIONAL, or HYPOTHESIS.")
    Save-Text ($lines -join [Environment]::NewLine) $handoffPath

    Write-Output ($summary | ConvertTo-Json -Depth 30)
    exit $(if (($failed + $blocked + $missing) -gt 0) { 2 } else { 0 })
} catch {
    [Console]::Error.WriteLine(([ordered]@{ error = $_.Exception.Message } | ConvertTo-Json -Compress))
    exit 2
}
