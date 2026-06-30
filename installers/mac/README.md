# macOS installers — Textural_Cardinality

## End users

1. Open Terminal in this folder (`installers/mac/`).
2. Run:
   ```bash
   chmod +x install-easy.sh
   ./install-easy.sh
   ```
3. Launch **Textural_Cardinality** from `~/Desktop/Textural_Cardinality.command` or `~/Applications/Textural_Cardinality/Launch-Textural_Cardinality.command`.

First run needs **Internet** and may take **10–25 minutes**.

Analysis uses exact event-boundary temporal sampling; see `TECHNICAL_MANUAL.md` in the repository root.

## Cloned repository

```bash
chmod +x install-and-run.sh setup-runtime.sh
./install-and-run.sh
```

## Developers

`./build-all.sh` — see `packaging/windows/` and publish binaries via **GitHub Releases**.
