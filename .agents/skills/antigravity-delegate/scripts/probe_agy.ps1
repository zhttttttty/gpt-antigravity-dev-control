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
    $savedPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $text = (& $Path @Arguments 2>&1 | ForEach-Object {
        if ($_ -is [System.Management.Automation.ErrorRecord]) { $_.Exception.Message } else { $_.ToString() }
    } | Out-String)
    $ErrorActionPreference = $savedPreference
    $exitCode = $LASTEXITCODE
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
    $agent = Invoke-Probe $path @("agent") (Join-Path $outDir "agent.log")
    $agents = Invoke-Probe $path @("agents") (Join-Path $outDir "agents.log")
    $agentList = Invoke-Probe $path @("agent", "list") (Join-Path $outDir "agent-list.log")
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
        agent_list_command = if ($agent.exit_code -eq 0) { "agent" } elseif ($agents.exit_code -eq 0) { "agents" } elseif ($agentList.exit_code -eq 0) { "agent list" } else { $null }
    }
    $result = [ordered]@{
        available = ($help.exit_code -eq 0)
        executable = $path
        version = $version
        help = $help
        agent_probes = [ordered]@{ agent = $agent; agents = $agents; agent_list = $agentList }
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
