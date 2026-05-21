# Textural cardinality — installers

**Repository:** https://github.com/LuisMRaimundo/Textural-Cardinality

This folder contains scripts to install **Textural cardinality** for users **without prior Python setup**. Open the folder for your operating system:

| Folder | System | Recommended entry point |
|--------|--------|-------------------------|
| **[`windows/`](windows/)** | Windows 10/11 (64-bit) | Double-click **`INSTALL.bat`** |
| **[`mac/`](mac/)** | macOS 11 or later | Run **`install-easy.sh`** |
| **[`linux/`](linux/)** | Linux (Ubuntu, Debian, Fedora, …) | Run **`install-easy.sh`** |

Each subfolder includes a **README** with platform-specific steps.

## What the standard installer does

1. Installs or detects **Python 3.10 or 3.11** (on Windows, installs automatically if missing).
2. Fetches source from **https://github.com/LuisMRaimundo/Textural-Cardinality** (`main` branch).
3. Creates an isolated environment and installs libraries from `requirements-install.txt`.
4. Adds a **shortcut** to launch the **Gradio** interface (vertical cardinality analysis).

The first run may take **10–25 minutes** (download plus scientific packages). An **Internet connection** is required.

## Not included in Git

Folders `runtime/`, `build/`, `dist/`, `output/`, and compiled `.exe` / `.zip` / `.dmg` / `.tar.gz` artefacts are **not** committed. To distribute ready-made binaries, use [GitHub Releases](https://github.com/LuisMRaimundo/Textural-Cardinality/releases).

## Portable builds (developers)

| Folder | Standard install | Portable build (PyInstaller) |
|--------|------------------|--------------------------------|
| `instalers/windows/` | `INSTALL.bat` | `Build-All.ps1` |
| `instalers/mac/` | `install-easy.sh` | `build-all.sh` |
| `instalers/linux/` | `install-easy.sh` | `build-all.sh` |

These build scripts wrap `packaging/windows/` (maintainers). End users should prefer **`INSTALL.bat`** / **`install-easy.sh`**.

## Run from a cloned repository (advanced)

If you already have the repo on disk, you can use the portable bootstrap (no GitHub download):

```text
instalers/windows/Install-and-Run.bat   (Windows)
instalers/mac/install-and-run.sh        (macOS)
instalers/linux/install-and-run.sh      (Linux)
```

That uses `instalers/common/bootstrap.py` to download a portable Python under `instalers/runtime/` and install the app in place.
