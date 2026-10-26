"""Install isolated integration prerequisites; never start a server or edit upstreams.

Uses Python's standard library and an explicitly pinned, preinstalled uv.
Without --install this only prints the intended versions and existing receipt.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
import zipfile

HERE = Path(__file__).resolve().parent
PINS = json.loads((HERE / "runtime-pins.json").read_text(encoding="utf-8"))


def run(args, *, env=None, capture=False):
    return subprocess.run([str(a) for a in args], check=True, env=env,
                          text=True, capture_output=capture, timeout=900)


def platform_key():
    system = {"Linux": "linux", "Windows": "win", "Darwin": "darwin"}.get(platform.system())
    arch = {"x86_64": "x64", "amd64": "x64", "aarch64": "arm64", "arm64": "arm64"}.get(platform.machine().lower())
    key = f"{system}-{arch}"
    if key not in PINS["node_archives"]:
        raise ValueError(f"Unsupported Node archive platform: {key}")
    return key


def safe_member(name, prefix):
    # Do not let downloaded archives write outside their owned staging folder.
    path = PurePosixPath(name)
    if "\\" in name or path.is_absolute() or ".." in path.parts or ":" in name:
        raise ValueError(f"Unsafe archive path: {name}")
    if not path.parts or path.parts[0] != prefix:
        raise ValueError(f"Unexpected archive root: {name}")
    return path


def extract_node(archive, target, prefix):
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as packed:
            for member in packed.infolist():
                safe_member(member.filename, prefix)
                if (member.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError("Node ZIP must not contain symlinks")
            packed.extractall(target)
    else:
        with tarfile.open(archive) as packed:
            for member in packed.getmembers():
                path = safe_member(member.name, prefix)
                if member.issym():
                    # Official npm/npx links are relative and remain inside this archive.
                    link = member.linkname
                    if "\\" in link or ":" in link or PurePosixPath(link).is_absolute():
                        raise ValueError("Unsafe Node symlink")
                    resolved = os.path.normpath(str(path.parent / link)).replace("\\", "/")
                    safe_member(resolved, prefix)
                elif not (member.isfile() or member.isdir()):
                    raise ValueError("Unexpected Node archive member type")
            # Explicit validation above also works on the existing Python 3.10 baseline.
            if hasattr(tarfile, "data_filter"):
                packed.extractall(target, filter="data")
            else:
                packed.extractall(target)


def node_install(root, key):
    info = PINS["node_archives"][key]
    prefix = f"node-v{PINS['node']}-{key}"
    dest = root / prefix
    executable = dest / ("node.exe" if key.startswith("win-") else "bin/node")
    if not executable.exists():
        with tempfile.TemporaryDirectory(prefix="node-stage-", dir=root) as stage:
            stage = Path(stage)
            archive = stage / f"{prefix}.{info['suffix']}"
            url = f"https://nodejs.org/dist/v{PINS['node']}/{archive.name}"
            with urllib.request.urlopen(url, timeout=60) as response, archive.open("wb") as output:
                shutil.copyfileobj(response, output)
            if hashlib.sha256(archive.read_bytes()).hexdigest() != info["sha256"]:
                raise ValueError("Node archive checksum mismatch")
            extract_node(archive, stage, prefix)
            if dest.exists():
                raise ValueError("Partial Node installation exists; inspect it before retrying")
            (stage / prefix).rename(dest)
    if run([executable, "--version"], capture=True).stdout.strip() != f"v{PINS['node']}":
        raise ValueError("Existing Node runtime does not match the pin")
    return executable


def install(root):
    key = platform_key()
    uv = shutil.which("uv")
    if not uv or run([uv, "--version"], capture=True).stdout.split()[1] != PINS["uv"]:
        raise ValueError(f"Install uv=={PINS['uv']} in a separate bootstrap environment first")
    if root.is_symlink():
        raise ValueError("Runtime root must not be a symlink")
    root = root.resolve()
    # Keep generated environments outside every application/source tree.
    source_root = HERE.parents[1].resolve()
    if root == source_root or source_root in root.parents or any(
            (parent / ".git").exists() for parent in (root, *root.parents)):
        raise ValueError("Choose a runtime root outside all Git repositories")
    marker = root / ".zenith-runtime-setup-v1"
    if root.exists() and any(root.iterdir()) and not marker.is_file():
        raise ValueError("Refusing an existing unowned nonempty runtime directory")
    root.mkdir(parents=True, exist_ok=True)
    minimum = 250 if marker.exists() else 700
    if shutil.disk_usage(root).free < minimum * 1024 * 1024:
        raise ValueError(f"At least {minimum} MiB free is required for setup; native runtimes need more")
    marker.touch(exist_ok=True)
    node = node_install(root, key)
    env = dict(os.environ)
    env["PATH"] = str(node.parent) + os.pathsep + env.get("PATH", "")
    env["UV_PYTHON_INSTALL_DIR"] = str(root / "python")
    env["UV_CACHE_DIR"] = str(root / "uv-cache")
    env["npm_config_cache"] = str(root / "npm-cache")
    env["npm_config_update_notifier"] = "false"
    npm_cli = node.parent / ("node_modules/npm/bin/npm-cli.js" if os.name == "nt" else "../lib/node_modules/npm/bin/npm-cli.js")
    tools = root / "node-tools"
    # No downloaded lifecycle scripts; never alter global Node/npm/pnpm.
    run([node, npm_cli, "install", "--prefix", tools, "--ignore-scripts", "--no-audit", "--no-fund",
         f"npm@{PINS['npm']}", f"pnpm@{PINS['pnpm']}"], env=env)
    lock = json.loads((tools / "package-lock.json").read_text(encoding="utf-8"))
    integrity = lock["packages"]["node_modules/pnpm"]["integrity"]
    expected = PINS["upstream"]["openclaw"]["package_manager_integrity"].split(".", 1)[1]
    if base64.b64decode(integrity.removeprefix("sha512-")).hex() != expected:
        raise ValueError("pnpm integrity differs from the audited OpenClaw packageManager")
    npm = tools / "node_modules/npm/bin/npm-cli.js"
    pnpm = tools / "node_modules/pnpm/bin/pnpm.mjs"
    for name, cli in [("npm", npm), ("pnpm", pnpm)]:
        if run([node, cli, "--version"], env=env, capture=True).stdout.strip() != PINS[name]:
            raise ValueError(f"Installed {name} version mismatch")
    run([uv, "python", "install", PINS["python"]], env=env)
    venv = root / "test-sdk-venv"
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists():
        run([uv, "venv", "--python", PINS["python"], "--managed-python", venv], env=env)
    if run([python, "-c", "import platform; print(platform.python_version())"], capture=True).stdout.strip() != PINS["python"]:
        raise ValueError("SDK Python version does not match pin")
    requirements = HERE / "requirements-test.txt"
    run([uv, "pip", "sync", "--python", python, "--require-hashes", "--only-binary", ":all:",
         "--no-cache", requirements], env=env)
    run([uv, "pip", "check", "--python", python], env=env)
    smoke = run([python, "-c", "import pytest, pytest_asyncio, openai, acp, httpx, websockets; print('test SDK imports passed')"], env=env, capture=True).stdout.strip()
    receipt = {"schema_version": 1, "node": str(node), "npm_cli": str(npm), "pnpm_cli": str(pnpm),
               "python": str(python), "python_install_dir": env["UV_PYTHON_INSTALL_DIR"],
               "pins": {k: PINS[k] for k in ("node", "npm", "pnpm", "python", "uv")},
               "requirements_sha256": hashlib.sha256(requirements.read_bytes()).hexdigest(),
               "sdk_smoke": smoke, "native_dependencies_installed": False,
               "integration_verified": False}
    temporary = root / "receipt.json.tmp"
    temporary.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    temporary.replace(root / "receipt.json")
    print(json.dumps(receipt, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="Dedicated directory outside all three source trees")
    parser.add_argument("--install", action="store_true", help="Download pinned prerequisites into --root")
    args = parser.parse_args(argv)
    if not args.install:
        print(json.dumps({"pins": PINS, "root": str(args.root), "install_requested": False}, indent=2))
        return 0
    try:
        install(args.root)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        parser.exit(1, f"Runtime setup failed: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
