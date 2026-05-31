# Windows installers — Textural cardinality

## End users (recommended)

1. Download this repository (or only the `installers/windows` folder from [GitHub](https://github.com/LuisMRaimundo/Textural-Cardinality)).
2. Double-click **`INSTALL.bat`**.
3. Wait until the window reports success (first run: **10–25 minutes**).
4. Start the app from **Desktop** or **Start menu → Textural cardinality**.

The application samples every event onset and offset automatically, so brief vertical states are not missed. See `TECHNICAL_MANUAL.md` in the repository root for details.

Install location: `%LOCALAPPDATA%\Programs\TexturalCardinality\`  
Log file: `install.log` in that folder.

## Already have the full repo cloned?

Use **`Install-and-Run.bat`** — installs a portable Python under `installers/runtime/` and runs the app from your copy (no re-download of source).

## Developers — frozen `.exe`

Run **`Build-All.ps1`** from PowerShell (requires Python + PyInstaller). See `packaging/windows/README.md`. Upload builds via **GitHub Releases** only.
