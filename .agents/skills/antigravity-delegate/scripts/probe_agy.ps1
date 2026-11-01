[CmdletBinding()]
param(
    [string]$Executable = "agy",
    [string]$OutputDir = ".ai/runtime/logs/probe",
    [string]$OutputFile = ""
)

$ErrorActionPreference = "Stop"

function Resolve-NativeExecutable([string]$Name) {
    $command = Get-Command $Name -ErrorAction Stop
    $path = if ($command.Source) { $command.Source } else { $command.Path }
    if (-not $path) { throw "Unable to resolve executable: $Name" }
    $extension = [IO.Path]::GetExtension($path).ToLowerInvariant()
    if ($extension -in @(".cmd", ".bat")) {
        throw "Use a native executable, not a batch wrapper: $path"
    }
    return [IO.Path]::GetFullPath($path)
}

function Invoke-Probe([string]$Path, [string[]]$Arguments, [string]$LogPath) {
    if ($Arguments.Count -ne 1 -or $Arguments[0] -notin @('--help', '--version')) {
        throw 'Probe accepts only --help or --version; never launch a prompt to inspect capabilities'
    }
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo.FileName = $Path
    $process.StartInfo.Arguments = $Arguments[0]
    $process.StartInfo.UseShellExecute = $false
    $process.StartInfo.CreateNoWindow = $true
    $process.StartInfo.RedirectStandardInput = $true
    $process.StartInfo.RedirectStandardOutput = $true
    $process.StartInfo.RedirectStandardError = $true
    try {
        if (-not $process.Start()) { throw 'Unable to start capability probe' }
        $process.StandardInput.Close()
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        $exitCode = 124
        if ($process.WaitForExit(15000)) {
            $exitCode = $process.ExitCode
        } else {
            & taskkill /PID $process.Id /T /F 2>&1 | Out-Null
            if (-not $process.HasExited) { $process.Kill() }
            $null = $process.WaitForExit(5000)
        }
        $text = if ($stdout.Wait(1000)) { $stdout.Result } else { '[stdout incomplete]' }
        $text += if ($stderr.Wait(1000)) { $stderr.Result } else { '[stderr incomplete]' }
        if ($exitCode -eq 124) { $text += "`nTIMEOUT: capability probe exceeded 15 seconds" }
    } finally {
        $process.Dispose()
    }
    Set-Content -LiteralPath $LogPath -Value $text -Encoding UTF8
    return [ordered]@{
        arguments = $Arguments
        exit_code = $exitCode
        log = $LogPath
        output_preview = $text.Trim().Substring(0, [Math]::Min(500, $text.Trim().Length))
    }
}

try {
    $path = Resolve-NativeExecutable $Executable
    $outDir = [IO.Path]::GetFullPath($OutputDir)
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null

    $version = Invoke-Probe $path @("--version") (Join-Path $outDir "version.log")
    $help = Invoke-Probe $path @("--help") (Join-Path $outDir "help.log")
    $helpText = Get-Content -LiteralPath (Join-Path $outDir "help.log") -Raw

    $modeValues = @()
    foreach ($candidate in @("accept-edits", "plan")) {
        if ($helpText -match [regex]::Escape($candidate)) { $modeValues += $candidate }
    }
    $capabilities = [ordered]@{
        permission_bypass = $helpText.Contains("--dangerously-skip-permissions")
        sandbox = $helpText.Contains("--sandbox")
        mode = $helpText.Contains("--mode")
        mode_values = @($modeValues)
        print_arg = if ($helpText.Contains("--print")) { "--print" } elseif ($helpText.Contains("-p")) { "-p" } else { $null }
        interactive_arg = if ($helpText.Contains("--prompt-interactive")) { "--prompt-interactive" } elseif ($helpText.Contains("-i")) { "-i" } else { $null }
        direct_is_controller_route = $true
        agent_list_command = $null
    }
    $result = [ordered]@{
        available = ($help.exit_code -eq 0)
        executable = $path
        version = $version
        help = $help
        agent_probes = [ordered]@{}
        capabilities = $capabilities
        login = "UNKNOWN"
        headless = "UNVERIFIED"
        generated_utc = [DateTime]::UtcNow.ToString("o")
    }
    $json = $result | ConvertTo-Json -Depth 10
    $capabilityPath = Join-Path $outDir "capabilities.json"
    Set-Content -LiteralPath $capabilityPath -Value $json -Encoding UTF8
    $result.capabilities_file = $capabilityPath
    $json = $result | ConvertTo-Json -Depth 10
    if ($OutputFile) {
        Set-Content -LiteralPath ([IO.Path]::GetFullPath($OutputFile)) -Value $json -Encoding UTF8
    }
    Write-Output $json
    exit $(if ($result.available) { 0 } else { 2 })
} catch {
    $errorResult = [ordered]@{
        available = $false
        executable = $Executable
        error = $_.Exception.Message
        login = "UNKNOWN"
        headless = "UNVERIFIED"
    }
    $json = $errorResult | ConvertTo-Json -Depth 10
    [Console]::Error.WriteLine($json)
    exit 2
}
