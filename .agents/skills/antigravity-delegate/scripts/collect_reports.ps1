[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$OutputDir,
    [int]$PreviewChars = 2000,
    [string]$OutputFile = ""
)

$ErrorActionPreference = "Stop"
try {
    $out = [IO.Path]::GetFullPath($OutputDir); $registryPath = Join-Path $out "sessions.json"
    $registry = Get-Content -LiteralPath $registryPath -Raw | ConvertFrom-Json
    $reports = @(); $failed = 0; $completed = 0
    foreach ($session in @($registry.sessions)) {
        $exists = Test-Path -LiteralPath $session.report; $preview = ""; if ($exists) { $text = Get-Content -LiteralPath $session.report -Raw; $preview = $text.Substring(0, [Math]::Min($PreviewChars, $text.Length)) }
        if ($session.status -eq "completed") { $completed++ }; if ($session.status -eq "failed") { $failed++ }
        $reports += [ordered]@{ name = $session.name; session_id = $session.session_id; status = $session.status; attempt = $session.attempt; report = $session.report; report_exists = $exists; preview = $preview; exit_code = $session.exit_code; execution_log = $session.execution_log; error_log = $session.error_log }
    }
    $summary = [ordered]@{ run_id = $registry.run_id; status = if ($failed -gt 0) { "FAILED" } elseif ($completed -eq @($registry.sessions).Count) { "COMPLETE" } else { "INCOMPLETE" }; total = @($registry.sessions).Count; completed = $completed; failed = $failed; reports = $reports; generated_utc = [DateTime]::UtcNow.ToString("o") }
    $json = $summary | ConvertTo-Json -Depth 20; if ($OutputFile) { Set-Content -LiteralPath ([IO.Path]::GetFullPath($OutputFile)) -Value $json -Encoding UTF8 }; Write-Output $json; exit $(if ($failed -gt 0) { 2 } else { 0 })
} catch { Write-Error (([ordered]@{ error = $_.Exception.Message } | ConvertTo-Json -Compress)); exit 2 }
