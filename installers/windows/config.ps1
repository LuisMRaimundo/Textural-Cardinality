# Textural cardinality — Windows installer constants
$script:TexturalCardinalityConfig = @{
    GitHubRepoUrl   = 'https://github.com/LuisMRaimundo/Textural-Cardinality'
    GitHubZipUrl    = 'https://github.com/LuisMRaimundo/Textural-Cardinality/archive/refs/heads/main.zip'
    GitHubZipFolder = 'Textural-Cardinality-main'
    GitHubBranch    = 'main'
    AppName         = 'Textural cardinality'
    PythonVersion   = '3.11'
    PythonMinMinor  = 10
    PythonMaxMinor  = 11
    PythonInstallerUrl = 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe'
    InstallRoot     = Join-Path $env:LOCALAPPDATA 'Programs\TexturalCardinality'
    LaunchScript    = 'textural-dimension'
}
