"""Build an allowlisted source ZIP and checksums; never include local configs or logs."""

import hashlib
from pathlib import Path
import tomllib
import zipfile


def source_files(root):
    names = [
        "pyproject.toml",
        "requirements.txt",
        "requirements-dev.txt",
        "README.md",
        "LICENSE",
        "MANIFEST.in",
        ".env.example",
        ".env.discord-test.example",
        ".gitignore",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
    ]
    files = [root / name for name in names]
    for directory in ("src/kumaops", "tests", "examples", "docs", ".github/workflows", "tools"):
        files.extend(
            p
            for p in (root / directory).rglob("*")
            if p.is_file() and p.suffix in {".py", ".md", ".yaml", ".yml", ".cjs"}
        )
    for path in files:
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("Refusing linked or out-of-tree release content")
    return sorted(set(files))


def main():
    root = Path(__file__).resolve().parents[1]
    output = root / "dist"
    output.mkdir(exist_ok=True)
    version = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "version"
    ]
    archive = output / f"kumaops-{version}-source.zip"
    files = source_files(root)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as stream:
        for path in files:
            stream.write(path, Path("kumaops") / path.relative_to(root))
    with zipfile.ZipFile(archive) as stream:
        if stream.testzip() is not None or len(stream.namelist()) != len(files):
            raise ValueError("Archive integrity check failed")
    artifacts = sorted(
        p for p in output.iterdir() if p.suffix in {".whl", ".zip"} or p.name.endswith(".tar.gz")
    )
    checksums = output / "SHA256SUMS.txt"
    checksums.write_text(
        "".join(
            hashlib.sha256(p.read_bytes()).hexdigest() + "  " + p.name + "\n" for p in artifacts
        ),
        encoding="utf-8",
    )
    print(f"Packaged {len(files)} source files; wrote dist/SHA256SUMS.txt")


if __name__ == "__main__":
    main()
