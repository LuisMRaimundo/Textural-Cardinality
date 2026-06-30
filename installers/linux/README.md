# Linux installers — Textural_Cardinality

## End users

```bash
cd installers/linux
chmod +x install-easy.sh
./install-easy.sh
```

Then run `~/.local/share/Textural_Cardinality/launch-textural-cardinality.sh` or `~/Desktop/Textural_Cardinality.sh`.

Requires **Python 3.10 or 3.11** and **unzip** / **curl** (usually preinstalled).

Analysis uses exact event-boundary temporal sampling; see `TECHNICAL_MANUAL.md` in the repository root.

## Cloned repository

```bash
chmod +x install-and-run.sh setup-runtime.sh
./install-and-run.sh
```

## Developers

`./build-all.sh` — publish frozen builds via **GitHub Releases** only.
