# Linux installers — Textural cardinality

## End users

```bash
cd installers/linux
chmod +x install-easy.sh
./install-easy.sh
```

Then run `~/.local/share/TexturalCardinality/launch-textural-cardinality.sh` or `~/Desktop/Textural-Cardinality.sh`.

Requires **Python 3.10 or 3.11** and **unzip** / **curl** (usually preinstalled).

## Cloned repository

```bash
chmod +x install-and-run.sh setup-runtime.sh
./install-and-run.sh
```

## Developers

`./build-all.sh` — publish frozen builds via **GitHub Releases** only.
