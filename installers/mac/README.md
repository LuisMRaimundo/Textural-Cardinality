# macOS installers — Textural cardinality

## End users

1. Open Terminal in this folder (`installers/mac/`).
2. Run:
   ```bash
   chmod +x install-easy.sh
   ./install-easy.sh
   ```
3. Launch **Textural cardinality** from `~/Desktop/Textural-Cardinality.command` or `~/Applications/TexturalCardinality/Launch-Textural-Cardinality.command`.

First run needs **Internet** and may take **10–25 minutes**.

Analysis uses exact event-boundary temporal sampling; see `TECHNICAL_MANUAL.md` in the repository root.

## Cloned repository

```bash
chmod +x install-and-run.sh setup-runtime.sh
./install-and-run.sh
```

## Developers

`./build-all.sh` — see `packaging/windows/` and publish binaries via **GitHub Releases**.
