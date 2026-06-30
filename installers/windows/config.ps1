# Textural_Cardinality — Windows installer constants
$script:Textural_CardinalityConfig = @{
    GitHubRepoUrl   = 'https://github.com/LuisMRaimundo/Textural_Cardinality'
    GitHubZipUrl    = 'https://github.com/LuisMRaimundo/Textural_Cardinality/archive/refs/heads/main.zip'
    GitHubZipFolder = 'Textural_Cardinality-main'
    GitHubBranch    = 'main'
    AppName         = 'Textural_Cardinality'
    PythonVersion   = '3.11'
    PythonMinMinor  = 10
    PythonMaxMinor  = 11
    PythonInstallerUrl = 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe'
    InstallRoot     = Join-Path $env:LOCALAPPDATA 'Programs\Textural_Cardinality'
    LaunchScript    = 'textural-cardinality'
}
