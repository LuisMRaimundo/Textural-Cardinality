#!/usr/bin/env python3
"""
Bootstrap portable Python + Textural cardinality dependencies, then launch the Gradio app.

Used by instalers/windows, instalers/mac, instalers/linux when running from a clone.
"""

from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
import webbrowser
import zipfile
from pathlib import Path

from config import (
    GRADIO_HOST,
    GRADIO_PORT_START,
    PROJECT_ROOT,
    RUNTIME_DIR,
    STAMP_FILE,
    machine_key,
    pbs_download_url,
    platform_key,
    runtime_python_dir,
    runtime_python_exe,
    windows_embed_zip_url,
)

GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"


def _log(msg: str) -> None:
    print(msg, flush=True)


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    _log(f"Downloading: {url}")
    urllib.request.urlretrieve(url, dest)  # noqa: S310


def _run(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    _log("Running: " + " ".join(cmd))
    subprocess.run(cmd, cwd=cwd or PROJECT_ROOT, env=env, check=True)


def _find_system_python() -> Path | None:
    for name in ("python3.11", "python3.10", "python3", "python"):
        exe = shutil.which(name)
        if not exe:
            continue
        try:
            out = subprocess.check_output(
                [exe, "-c", "import sys; print(sys.version_info[:2])"],
                text=True,
                timeout=30,
            ).strip()
            major, minor = (int(x) for x in out.strip("()").split(", "))
            if (major, minor) >= (3, 10) and (major, minor) <= (3, 11):
                return Path(exe)
        except (subprocess.CalledProcessError, OSError, ValueError):
            continue
    return None


def _setup_windows_embed() -> Path:
    py_exe = runtime_python_exe("windows")
    if py_exe.is_file():
        return py_exe

    runtime_dir = runtime_python_dir("windows")
    if runtime_dir.exists():
        shutil.rmtree(runtime_dir)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        zip_path = tmp_path / "python-embed.zip"
        _download(windows_embed_zip_url(), zip_path)
        runtime_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(runtime_dir)

    get_pip = runtime_dir / "get-pip.py"
    _download(GET_PIP_URL, get_pip)

    for pth in runtime_dir.glob("python*._pth"):
        text = pth.read_text(encoding="utf-8")
        if "import site" not in text:
            lines = [ln for ln in text.splitlines() if ln.strip() != "#import site"]
            if not any(ln.strip() == "import site" for ln in lines):
                lines.append("import site")
            pth.write_text("\n".join(lines) + "\n", encoding="utf-8")

    py_exe = runtime_python_exe("windows")
    _run([str(py_exe), str(get_pip)])
    return py_exe


def _setup_pbs(platform_name: str) -> Path:
    py_exe = runtime_python_exe(platform_name)
    if py_exe.is_file():
        return py_exe

    arch = machine_key()
    url = pbs_download_url(platform_name, arch)
    runtime_dir = runtime_python_dir(platform_name)
    if runtime_dir.exists():
        shutil.rmtree(runtime_dir)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        archive = tmp_path / "python.tar.gz"
        _download(url, archive)
        with tarfile.open(archive, "r:gz") as tf:
            tf.extractall(tmp_path)
        extracted = next(p for p in tmp_path.iterdir() if p.is_dir() and p.name.startswith("python"))
        shutil.move(str(extracted), str(runtime_dir))

    if not py_exe.is_file():
        raise RuntimeError(f"Portable Python not found after extract: {py_exe}")
    return py_exe


def ensure_portable_python() -> Path:
    plat = platform_key()
    existing = runtime_python_exe(plat)
    if existing.is_file():
        return existing

    _log(f"Setting up portable Python for {plat} …")
    if plat == "windows":
        return _setup_windows_embed()
    return _setup_pbs(plat)


def ensure_app_installed(py: Path) -> None:
    if STAMP_FILE.is_file():
        try:
            if STAMP_FILE.read_text(encoding="utf-8").strip() == _stamp_payload():
                return
        except OSError:
            pass

    req = PROJECT_ROOT / "requirements-install.txt"
    _log("Installing Textural cardinality dependencies (first run may take several minutes) …")
    _run([str(py), "-m", "pip", "install", "--upgrade", "pip", "wheel", "setuptools"])
    _run([str(py), "-m", "pip", "install", "-r", str(req)])
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    STAMP_FILE.write_text(_stamp_payload(), encoding="utf-8")
    _log("Install complete.")


def _stamp_payload() -> str:
    pyproject = PROJECT_ROOT / "pyproject.toml"
    return (
        f"v=1\nroot={PROJECT_ROOT.resolve()}\n"
        f"pyproject={pyproject.stat().st_mtime_ns if pyproject.is_file() else 0}\n"
    )


def _pick_free_port(host: str = GRADIO_HOST, start: int = GRADIO_PORT_START) -> int:
    for port in range(start, start + 64):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
            except OSError:
                continue
        return port
    raise RuntimeError(f"No free port on {host} in range {start}..{start + 63}")


def launch_gradio(py: Path) -> int:
    env = os.environ.copy()
    cache = Path(env.get("LOCALAPPDATA", env.get("HOME", "."))) / "TexturalCardinality" / "exports"
    env.setdefault("TEXTURAL_CARDINALITY_CACHE_DIR", str(cache))
    Path(env["TEXTURAL_CARDINALITY_CACHE_DIR"]).mkdir(parents=True, exist_ok=True)
    src_path = PROJECT_ROOT / "src"
    env["PYTHONPATH"] = (
        f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
        if env.get("PYTHONPATH")
        else str(src_path)
    )

    port = _pick_free_port()
    url = f"http://{GRADIO_HOST}:{port}/"
    _log(f"Starting Textural cardinality — open {url}")
    time.sleep(1.5)
    try:
        webbrowser.open(url)
    except OSError:
        pass

    code = (
        "from textural_dimension.ui.gradio_app import build_demo\n"
        f"build_demo().launch(server_name={GRADIO_HOST!r}, server_port={port}, inbrowser=False)\n"
    )
    return subprocess.call([str(py), "-c", code], cwd=PROJECT_ROOT, env=env)


def cmd_setup(_: argparse.Namespace) -> int:
    py = ensure_portable_python()
    ensure_app_installed(py)
    _log(f"Ready. Python: {py}")
    return 0


def cmd_launch(_: argparse.Namespace) -> int:
    py = ensure_portable_python()
    ensure_app_installed(py)
    return launch_gradio(py)


def cmd_doctor(_: argparse.Namespace) -> int:
    _log(f"Project root: {PROJECT_ROOT}")
    _log(f"Platform: {platform_key()} / {machine_key()}")
    py = runtime_python_exe(platform_key())
    _log(f"Portable Python: {py} ({'found' if py.is_file() else 'missing'})")
    _log(f"System Python (optional): {_find_system_python() or 'none'}")
    _log(f"Install stamp: {STAMP_FILE} ({'ok' if STAMP_FILE.is_file() else 'missing'})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Textural cardinality bootstrap")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("setup").set_defaults(func=cmd_setup)
    sub.add_parser("launch").set_defaults(func=cmd_launch)
    sub.add_parser("doctor").set_defaults(func=cmd_doctor)
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except subprocess.CalledProcessError as exc:
        _log(f"Command failed with exit code {exc.returncode}.")
        return exc.returncode or 1
    except Exception as exc:
        _log(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    if len(sys.argv) == 1:
        sys.argv.append("launch")
    raise SystemExit(main())
