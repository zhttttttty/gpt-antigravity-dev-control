[CmdletBinding()]
param(
    [string]$Repo = ".",
    [Parameter(Mandatory = $true)][string]$Path,
    [switch]$Force,
    [switch]$DeleteBranch,
    [string]$OutputFile = ""
)

$ErrorActionPreference = "Stop"

function Invoke-Git([string[]]$Arguments) {
    $savedPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $value = (& git @Arguments 2>&1 | ForEach-Object { $_.ToString() } | Out-String).Trim()
    $ErrorActionPreference = $savedPreference
    if ($LASTEXITCODE -ne 0) { throw "git $($Arguments -join ' ') failed: $value" }
    return $value
}

try {
    $repoPath = [IO.Path]::GetFullPath((Invoke-Git @("-C", $Repo, "rev-parse", "--show-toplevel")))
    $rootPath = [IO.Path]::GetFullPath((Join-Path $repoPath ".worktrees"))
    $target = [IO.Path]::GetFullPath($Path)
    $prefix = $rootPath.TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
    if (-not $target.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refuse to remove a path outside $rootPath"
    }
    $porcelain = (Invoke-Git @("-C", $repoPath, "worktree", "list", "--porcelain")) -replace '/', '\'
    if (-not ($porcelain -match [regex]::Escape("worktree $target"))) {
        throw "Path is not a registered Git worktree: $target"
    }
    if (Test-Path -LiteralPath $target) {
        $dirty = & git -C $target status --porcelain --untracked-files=all
        if ($dirty -and -not $Force) {
            throw "Worktree is dirty; refuse cleanup without -Force: $target"
        }
    }
    $branch = $null
    $blocks = $porcelain -split "(?m)^worktree "
    foreach ($block in $blocks) {
        if ($block -and $block.StartsWith($target + [Environment]::NewLine)) {
            $branchLine = ($block -split [Environment]::NewLine | Where-Object { $_ -like "branch *" } | Select-Object -First 1)
            if ($branchLine) { $branch = (($branchLine.Substring(7) -replace '^refs[\\/]+heads[\\/]+', '') -replace '\\', '/') }
        }
    }
    $removeArgs = @("-C", $repoPath, "worktree", "remove")
    if ($Force) { $removeArgs += "--force" }
    $removeArgs += $target
    Invoke-Git $removeArgs | Out-Null
    if ($DeleteBranch -and $branch) {
        Invoke-Git @("-C", $repoPath, "branch", "-D", $branch) | Out-Null
    }
    $result = [ordered]@{
        repo = $repoPath
        path = $target
        branch = $branch
        forced = [bool]$Force
        deleted_branch = [bool]($DeleteBranch -and $branch)
        removed_utc = [DateTime]::UtcNow.ToString("o")
    }
    $json = $result | ConvertTo-Json -Depth 6
    if ($OutputFile) { Set-Content -LiteralPath ([IO.Path]::GetFullPath($OutputFile)) -Value $json -Encoding UTF8 }
    Write-Output $json
    exit 0
} catch {
    [Console]::Error.WriteLine((@{ error = $_.Exception.Message } | ConvertTo-Json -Compress))
    exit 2
}
