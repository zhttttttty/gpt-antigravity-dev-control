[CmdletBinding()]
param(
    [string]$Repo = ".",
    [Parameter(Mandatory = $true)][string]$Path,
    [switch]$Force,
    [switch]$DeleteBranch,
    [string]$OutputFile = ""
)

$script = Join-Path $PSScriptRoot "remove_review_worktree.ps1"
& $script -Repo $Repo -Path $Path -Force:$Force -DeleteBranch:$DeleteBranch -OutputFile $OutputFile
exit $LASTEXITCODE
