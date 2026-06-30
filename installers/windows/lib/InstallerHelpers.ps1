# Shared helpers for Textural_Cardinality Windows one-click install

function Write-InstallLog {
    param([string]$Message, [string]$Level = 'INFO')
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] [$Level] $Message"
    if ($script:InstallLogPath) {
        Add-Content -LiteralPath $script:InstallLogPath -Value $line -Encoding UTF8
    }
    if ($Level -eq 'ERROR') { Write-Host $Message -ForegroundColor Red }
    elseif ($Level -eq 'WARN') { Write-Host $Message -ForegroundColor Yellow }
    else { Write-Host $Message }
}

function Find-ExistingPython {
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
        "$env:ProgramFiles\Python311\python.exe",
        "$env:ProgramFiles\Python310\python.exe"
    )
    foreach ($p in $candidates) {
        if (Test-Path $p) { return $p }
    }
    foreach ($name in @('python3.11', 'python3.10', 'python')) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if (-not $cmd) { continue }
        try {
            $minor = & $cmd.Source -c 'import sys; print(sys.version_info.minor)' 2>$null
            if ([int]$minor -ge $script:Textural_CardinalityConfig.PythonMinMinor -and
                [int]$minor -le $script:Textural_CardinalityConfig.PythonMaxMinor) {
                return $cmd.Source
            }
        } catch { }
    }
    return $null
}

function Install-Python311 {
    $cfg = $script:Textural_CardinalityConfig
    $installer = Join-Path $env:TEMP "python-$($cfg.PythonVersion)-amd64.exe"
    Write-InstallLog "Downloading Python $($cfg.PythonVersion) …"
    Invoke-WebRequest -Uri $cfg.PythonInstallerUrl -OutFile $installer -UseBasicParsing
    Write-InstallLog 'Installing Python (silent) …'
    $args = @('/quiet', 'InstallAllUsers=0', 'PrependPath=1', 'Include_test=0')
    $proc = Start-Process -FilePath $installer -ArgumentList $args -Wait -PassThru
    if ($proc.ExitCode -ne 0) {
        throw "Python installer exited with code $($proc.ExitCode)"
    }
    Start-Sleep -Seconds 3
    return Find-ExistingPython
}

function Initialize-AppSource {
    param(
        [string]$InstallerRoot,
        [string]$DestAppDir,
        [switch]$ForceRefresh
    )
    $cfg = $script:Textural_CardinalityConfig
    $marker = Join-Path $DestAppDir 'pyproject.toml'
    if ((Test-Path $marker) -and -not $ForceRefresh) {
        Write-InstallLog "Application source already present: $DestAppDir"
        return
    }
    if (Test-Path $DestAppDir) {
        Remove-Item -LiteralPath $DestAppDir -Recurse -Force
    }
    $tmp = Join-Path $env:TEMP ("textural-cardinality-src-" + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Force -Path $tmp | Out-Null
    $zipPath = Join-Path $tmp 'repo.zip'
    Write-InstallLog "Downloading from $($cfg.GitHubRepoUrl) …"
    Invoke-WebRequest -Uri $cfg.GitHubZipUrl -OutFile $zipPath -UseBasicParsing
    Expand-Archive -LiteralPath $zipPath -DestinationPath $tmp -Force
    $extracted = Join-Path $tmp $cfg.GitHubZipFolder
    if (-not (Test-Path $extracted)) {
        throw "Expected folder $($cfg.GitHubZipFolder) inside zip"
    }
    Move-Item -LiteralPath $extracted -Destination $DestAppDir
    Remove-Item -LiteralPath $tmp -Recurse -Force
    Write-InstallLog "Source installed to $DestAppDir"
}

function Initialize-PythonVenv {
    param(
        [string]$PythonExe,
        [string]$VenvDir,
        [string]$AppDir
    )
    if (-not (Test-Path $VenvDir)) {
        Write-InstallLog 'Creating virtual environment …'
        & $PythonExe -m venv $VenvDir
    }
    $venvPy = Join-Path $VenvDir 'Scripts\python.exe'
    $req = Join-Path $AppDir 'requirements-install.txt'
    if (-not (Test-Path $req)) {
        throw "Missing $req in application folder"
    }
    Write-InstallLog 'Installing Python packages (10–25 min first time) …'
    & $venvPy -m pip install --upgrade pip wheel setuptools
    & $venvPy -m pip install -r $req
}

function Test-TkAvailable {
    param([string]$VenvPython)
    try {
        & $VenvPython -c "import tkinter" 2>$null
        return $LASTEXITCODE -eq 0
    } catch { return $false }
}

function Register-Shortcuts {
    param(
        [string]$InstallRoot,
        [string]$AppDir,
        [string]$VenvDir
    )
    $cfg = $script:Textural_CardinalityConfig
    $launchBat = Join-Path $InstallRoot 'Launch-Textural_Cardinality.bat'
    $venvPy = Join-Path $VenvDir 'Scripts\python.exe'
    @"
@echo off
title $($cfg.AppName)
cd /d "$AppDir"
set "PYTHONPATH=$AppDir\src;%PYTHONPATH%"
"$venvPy" -m textural_dimension
if errorlevel 1 pause
"@ | Set-Content -LiteralPath $launchBat -Encoding ASCII

    $wsh = New-Object -ComObject WScript.Shell
    $desktop = [Environment]::GetFolderPath('Desktop')
    $startMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
    New-Item -ItemType Directory -Force -Path $startMenu | Out-Null

    foreach ($folder in @($desktop, $startMenu)) {
        $lnk = Join-Path $folder "$($cfg.AppName).lnk"
        $sc = $wsh.CreateShortcut($lnk)
        $sc.TargetPath = $launchBat
        $sc.WorkingDirectory = $InstallRoot
        $sc.Description = 'Textural_Cardinality vertical-cardinality analyser (Gradio)'
        $sc.Save()
    }
    Write-InstallLog "Shortcuts created (Desktop and Start menu)"
}
