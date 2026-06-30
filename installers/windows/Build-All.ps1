#Requires -Version 5.1
<#
.SYNOPSIS
  Build PyInstaller onedir bundle (developers). Output is not committed to git.
#>
$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$BuildScript = Join-Path $RepoRoot 'packaging\windows\build_windows.ps1'

if (-not (Test-Path $BuildScript)) {
    throw "Missing build script: $BuildScript"
}

Write-Host 'Textural_Cardinality — PyInstaller build (maintainer)' -ForegroundColor Cyan
Write-Host "Repository: $RepoRoot"
Write-Host 'Prerequisites: pip install -e . ; pip install pyinstaller'
Write-Host ''

Push-Location $RepoRoot
try {
    & $BuildScript @args
}
finally {
    Pop-Location
}

Write-Host ''
Write-Host 'Distribute dist\Textural_Cardinality\ via GitHub Releases (not git).' -ForegroundColor Yellow
