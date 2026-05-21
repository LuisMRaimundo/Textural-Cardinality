#Requires -Version 5.1
<#
.SYNOPSIS
  One-click installer for non-Python users: Python 3.11, GitHub source, pip deps, shortcuts.
#>
[CmdletBinding()]
param(
    [switch]$SkipPythonInstall,
    [switch]$ForceRefreshSource,
    [switch]$NoLaunch
)

$ErrorActionPreference = 'Stop'
$InstallerRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }

. (Join-Path $InstallerRoot 'config.ps1')
. (Join-Path $InstallerRoot 'lib\InstallerHelpers.ps1')

$cfg = $script:TexturalCardinalityConfig
$InstallRoot = $cfg.InstallRoot
$AppDir = Join-Path $InstallRoot 'app'
$VenvDir = Join-Path $InstallRoot 'venv'
$script:InstallLogPath = Join-Path $InstallRoot 'install.log'

New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null

Write-Host ''
Write-Host '========================================' -ForegroundColor Cyan
Write-Host ' Textural cardinality — Installer' -ForegroundColor Cyan
Write-Host ' ' $cfg.GitHubRepoUrl -ForegroundColor Cyan
Write-Host '========================================' -ForegroundColor Cyan
Write-Host ''

try {
    $pythonExe = Find-ExistingPython
    if (-not $pythonExe -and -not $SkipPythonInstall) {
        $pythonExe = Install-Python311
    }
    if (-not $pythonExe) {
        throw @"
Python 3.10 or 3.11 is required and was not found.
Run this installer again (it will install Python), or install from:
  https://www.python.org/downloads/
Then tick 'Add python.exe to PATH'.
"@
    }
    Write-InstallLog "Using Python: $pythonExe"

    Initialize-AppSource -InstallerRoot $InstallerRoot -DestAppDir $AppDir -ForceRefresh:$ForceRefreshSource
    Initialize-PythonVenv -PythonExe $pythonExe -VenvDir $VenvDir -AppDir $AppDir

    $venvPython = Join-Path $VenvDir 'Scripts\python.exe'
    if (-not (Test-TkAvailable -VenvPython $venvPython)) {
        Write-InstallLog 'WARNING: tkinter test failed. Reinstall Python from python.org with default options.' 'WARN'
    }

    Register-Shortcuts -InstallRoot $InstallRoot -AppDir $AppDir -VenvDir $VenvDir

    @"
Textural cardinality standard install
Installed: $(Get-Date -Format o)
Python: $pythonExe
Repo: $($cfg.GitHubRepoUrl)
"@ | Set-Content -LiteralPath (Join-Path $InstallRoot 'install-info.txt') -Encoding UTF8

    Write-Host ''
    Write-Host 'SUCCESS — Installation complete.' -ForegroundColor Green
    Write-Host " Location: $InstallRoot"
    Write-Host ' Start: Desktop or Start menu → Textural cardinality'
    Write-Host ''

    if (-not $NoLaunch) {
        $launch = Join-Path $InstallRoot 'Launch-Textural-Cardinality.bat'
        if (Test-Path $launch) {
            Write-InstallLog 'Launching Textural cardinality…'
            Start-Process -FilePath $launch
        }
    }
}
catch {
    Write-InstallLog $_.Exception.Message 'ERROR'
    if ($_.ScriptStackTrace) { Write-InstallLog $_.ScriptStackTrace 'ERROR' }
    Write-Host ''
    Write-Host 'INSTALLATION FAILED.' -ForegroundColor Red
    Write-Host $_.Exception.Message
    Write-Host "Log: $script:InstallLogPath"
    exit 1
}
