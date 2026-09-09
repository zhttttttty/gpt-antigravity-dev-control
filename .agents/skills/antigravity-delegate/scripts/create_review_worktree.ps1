[CmdletBinding()]
param(
    [string]$Repo = ".",
    [Parameter(Mandatory = $true)][string]$Name,
    [string]$BaseRef = "HEAD",
    [string]$WorktreeRoot = ".worktrees",
    [string]$OutputFile = "",
    [switch]$AllowDirty
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
    $status = & git -C $repoPath status --porcelain --untracked-files=all
    if (-not $AllowDirty -and $status) {
        throw "Main worktree is dirty; commit/stash changes or pass -AllowDirty explicitly"
    }
    $baseCommit = Invoke-Git @("-C", $repoPath, "rev-parse", $BaseRef)
    $slug = ($Name.ToLowerInvariant() -replace "[^a-z0-9._-]+", "-").Trim("-")
    if (-not $slug) { throw "Name must contain at least one alphanumeric character" }
    $stamp = [DateTime]::UtcNow.ToString("yyyyMMddHHmmssfff")
    $rootPath = [IO.Path]::GetFullPath((Join-Path $repoPath $WorktreeRoot))
    $target = [IO.Path]::GetFullPath((Join-Path $rootPath "review-$slug-$stamp"))
    $rootPrefix = $rootPath.TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
    if (-not $target.StartsWith($rootPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Resolved worktree path escapes worktree root: $target"
    }
    New-Item -ItemType Directory -Force -Path $rootPath | Out-Null
    $existing = (Invoke-Git @("-C", $repoPath, "worktree", "list", "--porcelain")) -replace '/', '\'
    if ($existing -match [regex]::Escape("worktree $target")) {
        throw "Worktree already exists: $target"
    }
    $branch = "ai/review/$slug-$stamp"
    Invoke-Git @("-C", $repoPath, "worktree", "add", "-b", $branch, $target, $baseCommit) | Out-Null
    $result = [ordered]@{
        repo = $repoPath
        path = $target
        branch = $branch
        base_ref = $BaseRef
        base_commit = $baseCommit
        worktree_root = $rootPath
        clean_before = [bool](-not $status)
        created_utc = [DateTime]::UtcNow.ToString("o")
    }
    $json = $result | ConvertTo-Json -Depth 6
    if ($OutputFile) { Set-Content -LiteralPath ([IO.Path]::GetFullPath($OutputFile)) -Value $json -Encoding UTF8 }
    Write-Output $json
    exit 0
} catch {
    [Console]::Error.WriteLine((@{ error = $_.Exception.Message } | ConvertTo-Json -Compress))
    exit 2
}
